CREATE TABLE recalls (
    id BIGSERIAL PRIMARY KEY,

    source TEXT NOT NULL DEFAULT 'FDA',
    source_recall_id TEXT NOT NULL,

    product_description TEXT NOT NULL,
    product_description_clean TEXT,

    brand_name TEXT,
    company_name TEXT,

    recall_reason TEXT,
    classification TEXT,
    status TEXT,

    recall_initiation_date DATE,
    report_date DATE,
    termination_date DATE,

    distribution_pattern TEXT,
    state TEXT,
    country TEXT,

    upc_codes TEXT[],
    lot_codes TEXT[],

    raw_data JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (source, source_recall_id)
);