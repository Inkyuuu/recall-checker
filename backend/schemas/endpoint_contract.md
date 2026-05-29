GET /api/recalls

Query params:
- q: optional string; supports case-insensitive substring and fuzzy matching
- source: optional FDA/USDA
- classification: optional string
- status: optional string
- state: optional string
- start_date: optional YYYY-MM-DD
- end_date: optional YYYY-MM-DD
- page: default 1
- page_size: default 20
- sort: default report_date_desc

Supported sort values:
- report_date_desc
- report_date_asc
- classification
- company_name
- relevance
