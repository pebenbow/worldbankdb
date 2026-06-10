CREATE TABLE IF NOT EXISTS public.dim_country (
    country_key  SERIAL       PRIMARY KEY,
    country_code VARCHAR(3)   NOT NULL UNIQUE,  -- ISO 3166-1 alpha-3
    country_name TEXT         NOT NULL,
    region       TEXT,
    income_group TEXT,
    lending_type TEXT,
    capital_city TEXT,
    longitude    NUMERIC(9,6),
    latitude     NUMERIC(9,6),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
