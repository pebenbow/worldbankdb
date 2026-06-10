-- etl_runner is created without a password intentionally. After the first
-- deploy, set it once via the Supabase dashboard (Database → Roles) or:
--   ALTER ROLE etl_runner WITH PASSWORD '...';
-- Then store the full connection string as the DATABASE_URL secret in GitHub.
CREATE ROLE etl_runner WITH LOGIN;

GRANT USAGE ON SCHEMA staging TO etl_runner;
GRANT USAGE ON SCHEMA public  TO etl_runner;

GRANT TRUNCATE, INSERT, SELECT
    ON staging.stg_wdi_raw
    TO etl_runner;

GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA staging
    TO etl_runner;

GRANT INSERT, UPDATE, SELECT
    ON public.dim_country,
       public.dim_indicator,
       public.dim_date,
       public.fact_wdi
    TO etl_runner;

GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA public
    TO etl_runner;

-- Future tables created by postgres in these schemas inherit the same grants.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT INSERT, UPDATE, SELECT ON TABLES TO etl_runner;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO etl_runner;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging
    GRANT TRUNCATE, INSERT, SELECT ON TABLES TO etl_runner;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging
    GRANT USAGE, SELECT ON SEQUENCES TO etl_runner;
