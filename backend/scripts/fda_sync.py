import httpx
from datetime import date
import os

import psycopg
from fda_transform import transform_record
from backfill_fda import save_recall

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required for FDA sync. Set it to your Postgres DSN, e.g. postgres://user:pass@host:5432/db"
    )

BASE_URL = "https://api.fda.gov/food/enforcement.json"


def parse_fda_date(value):
    if not value:
        return None
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def get_last_report_date(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(MAX(report_date), DATE '2004-01-01')
            FROM recalls
            WHERE source = 'FDA';
        """)
        return cur.fetchone()[0]


def get_latest_available_report_date():
    params = {
        "limit": 1,
        "sort": "report_date:desc",
    }
    response = httpx.get(BASE_URL, params=params)
    response.raise_for_status()
    records = response.json().get("results", [])
    if not records:
        raise RuntimeError("openFDA returned no enforcement records.")
    latest_report_date = parse_fda_date(records[0].get("report_date"))
    if not latest_report_date:
        raise RuntimeError("openFDA latest enforcement record has no report_date.")
    return latest_report_date


def fetch_fda_updates(start_date, end_date):
    params = {
        "search": f"report_date:[{start_date:%Y%m%d}+TO+{end_date:%Y%m%d}]",
        "limit": 1000,
        "sort": "report_date:asc"
    }

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            response = httpx.get(BASE_URL, params=params)
            response.raise_for_status()

            page = 0
            total_rows = 0

            while True:
                page += 1
                data = response.json()
                records = data.get("results", [])

                print(f"Processing page {page}, {len(records)} records")
                for record in records:
                    transformed = transform_record(record)
                    save_recall(cursor, transformed)
                    total_rows += 1

                conn.commit()

                next_link = response.headers.get("Link")
                if not next_link:
                    print(f"No more pages. Sync complete. Total records processed: {total_rows}")
                    break

                next_url = next_link.split("<")[1].split(">")[0]
                response = httpx.get(next_url)
                response.raise_for_status()


def run_sync():
    today = date.today()
    latest_available_report_date = get_latest_available_report_date()

    with psycopg.connect(DATABASE_URL) as conn:
        start_report_date = get_last_report_date(conn)

    if start_report_date > today:
        raise RuntimeError("Last report_date is in the future. Check the database contents.")

    end_report_date = min(today, latest_available_report_date)
    if start_report_date >= end_report_date:
        print(
            "No FDA updates to sync. "
            f"Database latest report_date is {start_report_date}; "
            f"openFDA latest available report_date is {latest_available_report_date}."
        )
        return

    print(f"Syncing FDA updates from {start_report_date} through {end_report_date}")
    fetch_fda_updates(start_report_date, end_report_date)


if __name__ == "__main__":
    run_sync()
