CREATE TABLE IF NOT EXISTS public.dim_indicator (
    indicator_key  SERIAL       PRIMARY KEY,
    indicator_code VARCHAR(50)  NOT NULL UNIQUE,
    indicator_name TEXT         NOT NULL,
    topic          TEXT,
    source_note    TEXT,
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
