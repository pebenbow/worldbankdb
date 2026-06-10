CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.stg_wdi_raw (
    id             BIGSERIAL    PRIMARY KEY,
    country_code   VARCHAR(3)   NOT NULL,
    country_name   TEXT         NOT NULL,
    indicator_code VARCHAR(50)  NOT NULL,
    indicator_name TEXT         NOT NULL,
    year           INTEGER      NOT NULL,
    value          NUMERIC,
    unit           TEXT,
    obs_status     TEXT,
    loaded_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stg_wdi_raw_lookup
    ON staging.stg_wdi_raw (country_code, indicator_code, year);
