import re
from datetime import datetime

def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y%m%d").date()

def clean_text(text):
    if not text:
        return None
    text = text.lower().strip()
    return re.sub(r"[^\w\s]", "", text)

def extract_upcs(code_info):
    if not code_info:
        return []
    return re.findall(r"\b\d{8,13}\b", code_info)

def extract_lots(code_info, more_code_info):
    codes = []
    for text in (code_info, more_code_info):
        if not text:
            continue
        matches = re.findall(r"(?:Lot|LOT|lot)\s*No\.?\s*([^\.;,]+)", text)
        codes.extend(m.strip() for m in matches if m.strip())
    return list(dict.fromkeys(codes))

def transform_record(record):
    code_info = record.get("code_info", "") or ""
    more_code_info = record.get("more_code_info", "") or ""

    return {
        "source": "FDA",
        "source_recall_id": record.get("recall_number") or record.get("event_id"),
        "product_description": record.get("product_description"),
        "product_description_clean": clean_text(record.get("product_description")),
        "brand_name": (record.get("openfda") or {}).get("brand_name", [None])[0],
        "company_name": record.get("recalling_firm"),
        "recall_reason": record.get("reason_for_recall"),
        "classification": record.get("classification"),
        "status": record.get("status"),
        "recall_initiation_date": parse_date(record.get("recall_initiation_date")),
        "report_date": parse_date(record.get("report_date")),
        "termination_date": parse_date(record.get("termination_date")),
        "distribution_pattern": record.get("distribution_pattern"),
        "state": record.get("state"),
        "country": record.get("country"),
        "upc_codes": list(dict.fromkeys(
            (record.get("openfda") or {}).get("upc", []) + extract_upcs(code_info)
        )),
        "lot_codes": extract_lots(code_info, more_code_info),
        "raw_data": record,
    }