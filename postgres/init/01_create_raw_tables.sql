-- data assets are materialized only in the raw and marts layers.
-- the staging layer only contains views.
-- see `dbt_projects.yml` for semantic definitions

-- json payloads are stored intact (envelope pattern)
CREATE TABLE raw.premium_transactions_raw (
    ingestion_run_id TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_json JSONB NOT NULL,
    payload_hash TEXT NOT NULL,
    source_file TEXT,
    CONSTRAINT uq_premium_transactions_raw_payload_hash UNIQUE (payload_hash)
);