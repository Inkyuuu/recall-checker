import os
import json
import httpx
import importlib.util
from fda_transform import transform_record
import psycopg

BASE_URL = "https://api.fda.gov/food/enforcement.json"

params = {
    "limit": 1000,
    "sort": "report_date:asc"
}


def get_database_url():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required to save recalls. Set it to your Postgres DSN, e.g. postgres://user:pass@host:5432/db"
        )
    return database_url


def get_db_module():
    if importlib.util.find_spec("psycopg"):
        import psycopg
        return psycopg
    if importlib.util.find_spec("psycopg2"):
        import psycopg2
        return psycopg2
    raise RuntimeError(
        "Install psycopg or psycopg2 in the backend virtualenv before running this script."
    )


def save_recall(cursor, transformed):
    sql = """
        INSERT INTO recalls (
            source,
            source_recall_id,
            product_description,
            product_description_clean,
            brand_name,
            company_name,
            recall_reason,
            classification,
            status,
            recall_initiation_date,
            report_date,
            termination_date,
            distribution_pattern,
            state,
            country,
            upc_codes,
            lot_codes,
            raw_data
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (source, source_recall_id) DO UPDATE SET
            product_description = EXCLUDED.product_description,
            product_description_clean = EXCLUDED.product_description_clean,
            brand_name = EXCLUDED.brand_name,
            company_name = EXCLUDED.company_name,
            recall_reason = EXCLUDED.recall_reason,
            classification = EXCLUDED.classification,
            status = EXCLUDED.status,
            recall_initiation_date = EXCLUDED.recall_initiation_date,
            report_date = EXCLUDED.report_date,
            termination_date = EXCLUDED.termination_date,
            distribution_pattern = EXCLUDED.distribution_pattern,
            state = EXCLUDED.state,
            country = EXCLUDED.country,
            upc_codes = EXCLUDED.upc_codes,
            lot_codes = EXCLUDED.lot_codes,
            raw_data = EXCLUDED.raw_data,
            updated_at = NOW()
    """
    cursor.execute(
        sql,
        [
            transformed["source"],
            transformed["source_recall_id"],
            transformed["product_description"],
            transformed["product_description_clean"],
            transformed["brand_name"],
            transformed["company_name"],
            transformed["recall_reason"],
            transformed["classification"],
            transformed["status"],
            transformed["recall_initiation_date"],
            transformed["report_date"],
            transformed["termination_date"],
            transformed["distribution_pattern"],
            transformed["state"],
            transformed["country"],
            transformed["upc_codes"],
            transformed["lot_codes"],
            json.dumps(transformed["raw_data"]),
        ],
    )


def run_backfill():
    database_url = get_database_url()
    db_module = get_db_module()

    with db_module.connect(database_url) as conn:
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
                    print(f"No more pages. Backfill complete. Total records processed: {total_rows}")
                    break

                next_url = next_link.split("<")[1].split(">")[0]
                response = httpx.get(next_url)
                response.raise_for_status()


if __name__ == "__main__":
    run_backfill()
