import os
from datetime import datetime, date
from math import ceil
from flask import Blueprint, jsonify, request
import psycopg
from psycopg.rows import dict_row

recalls_bp = Blueprint("recalls", __name__, url_prefix="/api")

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50
DATE_FORMAT = "%Y-%m-%d"
FUZZY_SEARCH_THRESHOLD = 0.3
VALID_SORTS = {
    "report_date_desc": "report_date DESC NULLS LAST",
    "report_date_asc": "report_date ASC NULLS LAST",
    "classification": "classification ASC NULLS LAST",
    "company_name": "company_name ASC NULLS LAST",
    "relevance": "search_rank DESC NULLS LAST, report_date DESC NULLS LAST",
}
VALID_SOURCES = {"FDA", "USDA"}

SELECT_COLUMNS = [
    "source",
    "source_recall_id",
    "product_description",
    "product_description_clean",
    "brand_name",
    "company_name",
    "recall_reason",
    "classification",
    "status",
    "recall_initiation_date",
    "report_date",
    "termination_date",
    "distribution_pattern",
    "state",
    "country",
    "upc_codes",
    "lot_codes",
    "raw_data",
]

SEARCHABLE_COLUMNS = [
    "product_description",
    "product_description_clean",
    "brand_name",
    "company_name",
    "recall_reason",
]

SEARCH_VECTOR_SQL = (
    "to_tsvector('english', "
    "COALESCE(product_description, '') || ' ' || "
    "COALESCE(product_description_clean, '') || ' ' || "
    "COALESCE(brand_name, '') || ' ' || "
    "COALESCE(company_name, '') || ' ' || "
    "COALESCE(recall_reason, '')"
    ")"
)

SEARCH_SYNONYMS = {
    "beef": ["ground beef", "meat"],
    "chicken": ["poultry"],
    "poultry": ["chicken", "turkey"],
    "turkey": ["poultry"],
    "pork": ["meat"],
    "milk": ["dairy"],
    "cheese": ["dairy"],
    "dairy": ["milk", "cheese"],
    "egg": ["eggs"],
    "eggs": ["egg"],
    "fish": ["seafood"],
    "shrimp": ["seafood"],
    "seafood": ["fish", "shrimp"],
    "e coli": ["ecoli", "escherichia coli", "shiga toxin"],
    "ecoli": ["e coli", "escherichia coli", "shiga toxin"],
    "escherichia coli": ["e coli", "ecoli"],
    "listeria": ["listeria monocytogenes"],
    "salmonella": ["salmonella contamination"],
    "allergy": ["allergen", "undeclared"],
    "allergen": ["allergy", "undeclared"],
    "undeclared": ["allergen", "allergy"],
    "foreign material": ["extraneous material"],
    "plastic": ["foreign material", "extraneous material"],
}


def expand_search_terms(query):
    normalized_query = " ".join(query.lower().split())
    terms = [query]
    for key, synonyms in SEARCH_SYNONYMS.items():
        if key in normalized_query:
            terms.extend(synonyms)
    return list(dict.fromkeys(term for term in terms if term))


def quote_websearch_term(term):
    return f'"{term.replace(chr(34), " ")}"'


def websearch_query(terms):
    return " OR ".join(quote_websearch_term(term) for term in terms)


def search_rank_sql():
    trigram_rank = "GREATEST(" + ", ".join(
        f"similarity(COALESCE({column}, ''), %s)" for column in SEARCHABLE_COLUMNS
    ) + ")"
    full_text_rank = (
        f"ts_rank_cd({SEARCH_VECTOR_SQL}, websearch_to_tsquery('english', %s))"
    )
    return f"({trigram_rank} + {full_text_rank})"


def get_database_url():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required. Set it to your Postgres DSN, e.g. postgres://user:pass@host:5432/db"
        )
    return database_url


def parse_date(date_string, name):
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, DATE_FORMAT).date()
    except ValueError:
        raise ValueError(
            f"Invalid {name}; expected format YYYY-MM-DD, got: {date_string}"
        )


def normalize_int(value, default, minimum=1, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if result < minimum:
        return default
    if maximum is not None and result > maximum:
        return maximum
    return result


def serialize_row(row):
    result = {}
    for key, value in row.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def build_filters(args):
    filters = []
    params = []
    search_rank_params = []

    q = args.get("q")
    if q:
        q = q.strip()
        if q:
            search_terms = expand_search_terms(q)
            full_text_query = websearch_query(search_terms)
            substring_matches = [
                f"{column} ILIKE %s" for column in SEARCHABLE_COLUMNS
                for _ in search_terms
            ]
            fuzzy_matches = [
                f"{column} %% %s"
                for column in SEARCHABLE_COLUMNS
            ]
            full_text_match = f"{SEARCH_VECTOR_SQL} @@ websearch_to_tsquery('english', %s)"
            filters.append(
                "(" + " OR ".join(substring_matches + fuzzy_matches + [full_text_match]) + ")"
            )
            for column in SEARCHABLE_COLUMNS:
                for term in search_terms:
                    params.append(f"%{term}%")
            for _ in SEARCHABLE_COLUMNS:
                params.append(q)
            params.append(full_text_query)
            search_rank_params = [q] * len(SEARCHABLE_COLUMNS) + [full_text_query]

    source = args.get("source")
    if source:
        source = source.strip().upper()
        if source not in VALID_SOURCES:
            raise ValueError("source must be FDA or USDA")
        filters.append("source = %s")
        params.append(source)

    classification = args.get("classification")
    if classification:
        filters.append("classification ILIKE %s")
        params.append(classification)

    status = args.get("status")
    if status:
        filters.append("status ILIKE %s")
        params.append(f"%{status}%")

    state = args.get("state")
    if state:
        filters.append("state ILIKE %s")
        params.append(f"%{state}%")

    start_date = parse_date(args.get("start_date"), "start_date")
    if start_date:
        filters.append("report_date >= %s")
        params.append(start_date)

    end_date = parse_date(args.get("end_date"), "end_date")
    if end_date:
        filters.append("report_date <= %s")
        params.append(end_date)

    return filters, params, search_rank_params


@recalls_bp.route("/recalls", methods=["GET"])
def list_recalls():
    page = normalize_int(request.args.get("page"), DEFAULT_PAGE)
    page_size = normalize_int(request.args.get("page_size"), DEFAULT_PAGE_SIZE, maximum=MAX_PAGE_SIZE)

    sort_key = request.args.get("sort", "report_date_desc")
    order_by = VALID_SORTS.get(sort_key)
    if order_by is None:
        return jsonify({"error": "sort must be one of report_date_desc, report_date_asc, classification, company_name, relevance"}), 400

    try:
        filters, params, search_rank_params = build_filters(request.args)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if sort_key == "relevance" and not search_rank_params:
        order_by = VALID_SORTS["report_date_desc"]

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    count_sql = f"SELECT COUNT(*) AS total FROM recalls {where_clause}"
    select_columns = ", ".join(SELECT_COLUMNS)
    select_params = params
    if search_rank_params:
        select_columns = f"{select_columns}, {search_rank_sql()} AS search_rank"
        select_params = search_rank_params + params

    select_sql = f"SELECT {select_columns} FROM recalls {where_clause} ORDER BY {order_by} LIMIT %s OFFSET %s"

    offset = (page - 1) * page_size
    params_for_select = select_params + [page_size, offset]

    database_url = get_database_url()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        if search_rank_params:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
                    [str(FUZZY_SEARCH_THRESHOLD)],
                )

        with conn.cursor() as cur:
            cur.execute(count_sql, params)
            total = cur.fetchone()["total"]

        with conn.cursor() as cur:
            cur.execute(select_sql, params_for_select)
            rows = cur.fetchall()

    items = [serialize_row(row) for row in rows]
    total_pages = ceil(total / page_size) if total else 0

    return jsonify(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "items": items,
        }
    )
