CREATE TABLE IF NOT EXISTS public.fact_wdi (
    fact_key      BIGSERIAL PRIMARY KEY,
    country_key   INTEGER   NOT NULL REFERENCES public.dim_country(country_key),
    indicator_key INTEGER   NOT NULL REFERENCES public.dim_indicator(indicator_key),
    date_key      INTEGER   NOT NULL REFERENCES public.dim_date(date_key),
    value         NUMERIC,
    obs_status    TEXT,
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (country_key, indicator_key, date_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_wdi_country   ON public.fact_wdi (country_key);
CREATE INDEX IF NOT EXISTS idx_fact_wdi_indicator ON public.fact_wdi (indicator_key);
CREATE INDEX IF NOT EXISTS idx_fact_wdi_date      ON public.fact_wdi (date_key);
