CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS recalls_product_description_trgm_idx
    ON recalls USING GIN (product_description gin_trgm_ops);

CREATE INDEX IF NOT EXISTS recalls_product_description_clean_trgm_idx
    ON recalls USING GIN (product_description_clean gin_trgm_ops);

CREATE INDEX IF NOT EXISTS recalls_brand_name_trgm_idx
    ON recalls USING GIN (brand_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS recalls_company_name_trgm_idx
    ON recalls USING GIN (company_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS recalls_recall_reason_trgm_idx
    ON recalls USING GIN (recall_reason gin_trgm_ops);

CREATE INDEX IF NOT EXISTS recalls_search_vector_idx
    ON recalls USING GIN (
        to_tsvector(
            'english',
            COALESCE(product_description, '') || ' ' ||
            COALESCE(product_description_clean, '') || ' ' ||
            COALESCE(brand_name, '') || ' ' ||
            COALESCE(company_name, '') || ' ' ||
            COALESCE(recall_reason, '')
        )
    );

CREATE INDEX IF NOT EXISTS recalls_report_date_idx
    ON recalls (report_date DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS recalls_source_idx
    ON recalls (source);

CREATE INDEX IF NOT EXISTS recalls_source_report_date_idx
    ON recalls (source, report_date DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS recalls_classification_idx
    ON recalls (classification);

CREATE INDEX IF NOT EXISTS recalls_status_idx
    ON recalls (status);

CREATE INDEX IF NOT EXISTS recalls_state_idx
    ON recalls (state);

CREATE INDEX IF NOT EXISTS recalls_company_name_idx
    ON recalls (company_name);

ANALYZE recalls;
