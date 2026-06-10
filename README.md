# World Bank Development Indicators — Data Warehouse

A PostgreSQL data warehouse built on [Supabase](https://supabase.com) that stores yearly [World Development Indicators](https://datatopics.worldbank.org/world-development-indicators/) (WDI) for every country. The schema follows the Kimball star schema methodology. Data is loaded via an ELT pipeline that extracts from the World Bank public API, bulk-loads into a staging table, and transforms into dimensions and facts using SQL upserts. Schema migrations and ETL runs are automated through GitHub Actions.

---

## Architecture

### Schema layers

| Layer | Schema | Purpose |
|---|---|---|
| Staging | `staging` | Raw API data, loaded as-is. Never exposed via the Supabase REST API. |
| Dimensions | `public` | Conformed descriptors for country, indicator, and year. SCD Type 1 (in-place updates). |
| Facts | `public` | One row per `(country, indicator, year)` with the observed value. |

### ELT flow

```mermaid
flowchart LR
    API(["World Bank API"])
    STG[("staging.stg_wdi_raw")]
    DIM["dim_country\ndim_indicator\ndim_date"]
    FACT[("fact_wdi")]

    API -- "extract.py + load.py\npaginated HTTP, bulk insert" --> STG
    STG -- "transform.py\nSQL upsert" --> DIM
    DIM & STG -- "transform.py\nSQL JOIN + upsert" --> FACT
```

The transform step runs entirely in the database. No data is held in application memory beyond the staging load.

---

## Repository Structure

```
.
├── .github/
│   └── workflows/
│       ├── ci.yml          # Validate migrations and run tests on every PR
│       ├── deploy.yml      # Push migrations to Supabase on merge to main
│       └── etl.yml         # Run the WDI pipeline (scheduled annually or on demand)
│
├── schema/                 # Human-readable DDL — source of truth for table design
│   ├── staging/
│   │   └── stg_wdi_raw.sql
│   ├── dimensions/
│   │   ├── dim_country.sql
│   │   ├── dim_indicator.sql
│   │   └── dim_date.sql
│   └── facts/
│       └── fact_wdi.sql
│
├── supabase/
│   ├── config.toml         # Local Supabase CLI configuration
│   └── migrations/         # Append-only, timestamped migration files
│       ├── 20260609000001_create_staging.sql
│       ├── 20260609000002_create_dim_country.sql
│       ├── 20260609000003_create_dim_indicator.sql
│       ├── 20260609000004_create_dim_date.sql
│       ├── 20260609000005_create_fact_wdi.sql
│       └── 20260609000006_create_etl_runner.sql
│
├── etl/
│   ├── extract.py          # World Bank API → Python dicts
│   ├── load.py             # Python dicts → staging table (bulk insert)
│   ├── transform.py        # SQL upserts: staging → dims → facts
│   └── pipeline.py         # Orchestrates extract → load → transform
│
├── tests/
│   ├── conftest.py         # DB fixture and session-scoped seed data
│   ├── test_schema.py      # Table, column, constraint, and index assertions
│   └── test_data_quality.py # Grain, referential integrity, and idempotency tests
│
├── .env.example
├── pyproject.toml
└── README.md
```

> **`schema/` vs `supabase/migrations/`** — `schema/` contains clean, readable DDL for reference and code review. `supabase/migrations/` contains the same DDL in timestamped, append-only files that the Supabase CLI applies in order. When making a schema change, add a new migration file; never edit an existing one.

---

## Data Model

### `staging.stg_wdi_raw`

Landing zone for raw API data. Truncated and reloaded on every pipeline run.

| Column | Type | Notes |
|---|---|---|
| `id` | `bigserial` | Surrogate PK |
| `country_code` | `varchar(3)` | ISO 3166-1 alpha-3 |
| `country_name` | `text` | |
| `indicator_code` | `varchar(50)` | World Bank indicator ID |
| `indicator_name` | `text` | |
| `year` | `integer` | |
| `value` | `numeric` | Nullable — not all country/year combinations have data |
| `unit` | `text` | |
| `obs_status` | `text` | World Bank observation status flag |
| `loaded_at` | `timestamptz` | Set by database default |

### `public.dim_country`

One row per sovereign country. Aggregates (regions, income groups) are excluded at extraction time.

| Column | Type | Notes |
|---|---|---|
| `country_key` | `serial` | Surrogate PK |
| `country_code` | `varchar(3)` | ISO 3166-1 alpha-3, unique |
| `country_name` | `text` | |
| `region` | `text` | World Bank region classification |
| `income_group` | `text` | World Bank income level |
| `lending_type` | `text` | |
| `capital_city` | `text` | |
| `longitude` | `numeric(9,6)` | |
| `latitude` | `numeric(9,6)` | |
| `updated_at` | `timestamptz` | Updated on every upsert |

### `public.dim_indicator`

One row per World Development Indicator.

| Column | Type | Notes |
|---|---|---|
| `indicator_key` | `serial` | Surrogate PK |
| `indicator_code` | `varchar(50)` | World Bank indicator ID, unique |
| `indicator_name` | `text` | |
| `topic` | `text` | Broad topic category |
| `source_note` | `text` | World Bank methodology note |
| `updated_at` | `timestamptz` | Updated on every upsert |

### `public.dim_date`

One row per year present in the staging data.

| Column | Type | Notes |
|---|---|---|
| `date_key` | `serial` | Surrogate PK |
| `year` | `integer` | Unique |
| `decade` | `integer` | Generated: `year / 10 * 10` |
| `century` | `integer` | Generated: `year / 100 * 100` |

### `public.fact_wdi`

Grain: one row per `(country, indicator, year)`.

| Column | Type | Notes |
|---|---|---|
| `fact_key` | `bigserial` | Surrogate PK |
| `country_key` | `integer` | FK → `dim_country` |
| `indicator_key` | `integer` | FK → `dim_indicator` |
| `date_key` | `integer` | FK → `dim_date` |
| `value` | `numeric` | Observed value; nullable |
| `obs_status` | `text` | Carried over from staging |
| `loaded_at` | `timestamptz` | Set on insert, updated on upsert |

The unique constraint on `(country_key, indicator_key, date_key)` makes all fact loads idempotent — rerunning the pipeline updates values in place without creating duplicates.

---

## CI/CD Workflows

### `ci.yml` — Pull request validation

Triggered on every PR to `main`. Starts a local Supabase instance via Docker, applies all migrations from scratch with `supabase db reset`, installs Python dependencies, and runs the test suite. No production credentials are used.

### `deploy.yml` — Migration deployment

Triggered on push to `main` (i.e., after a PR merges). Links the Supabase CLI to the production project and runs `supabase db push`, which applies any migration files not yet recorded in the remote migration history table. Runs in the `supabase_prod` GitHub environment.

### `etl.yml` — Data pipeline

Triggered on a schedule (06:00 UTC, January 2nd each year) or manually via `workflow_dispatch`. Runs in the `supabase_prod` GitHub environment. Manual runs accept three optional inputs:

| Input | Default | Description |
|---|---|---|
| `start_year` | `2020` | First year to fetch |
| `end_year` | `2023` | Last year to fetch |
| `indicator_codes` | *(empty)* | Comma-separated indicator codes; leave empty to fetch all ~1,400 WDI indicators |

The full WDI run (~1,400 indicators × 200 countries × year range) can take several hours. Use the `indicator_codes` input to scope a partial run.

---

## Setup

### Prerequisites

- Python 3.11+
- [Supabase CLI](https://supabase.com/docs/guides/cli/getting-started)
- Docker (required by the Supabase CLI for local development)
- A Supabase project

### Local development

```bash
# Install Python dependencies
pip install -e ".[dev]"

# Start local Supabase (applies migrations automatically)
supabase start

# Reset the database and re-apply all migrations
supabase db reset

# Run the test suite
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres pytest tests/ -v

# Stop Supabase
supabase stop
```

### Environment variables

Copy `.env.example` to `.env` and fill in your values:

```
DATABASE_URL=postgresql://etl_runner.[project-ref]:[password]@[pooler-host].pooler.supabase.com:6543/postgres
WB_START_YEAR=2020
WB_END_YEAR=2023
```

### GitHub secrets

All production secrets live in the `supabase_prod` GitHub environment (Settings → Environments → supabase_prod).

| Secret | Used by | Description |
|---|---|---|
| `SUPABASE_ACCESS_TOKEN` | `deploy.yml` | Personal access token from supabase.com/dashboard/account/tokens |
| `SUPABASE_PROJECT_REF` | `deploy.yml` | Project reference ID from the Supabase dashboard URL |
| `SUPABASE_DB_PASSWORD` | `deploy.yml` | `postgres` superuser password — required by `supabase db push` |
| `DATABASE_URL` | `etl.yml` | Full connection string for the `etl_runner` role. Use port `6543` (PgBouncer transaction mode). Find the pooler host in the Supabase dashboard under Project Settings → Database → Connection pooling. |

### First-deploy checklist

The `etl_runner` role is created by migration 6 without a password. After the first successful deploy:

1. In the Supabase dashboard, open the SQL editor and run:
   ```sql
   ALTER ROLE etl_runner WITH PASSWORD 'your-strong-password';
   ```
2. Add `DATABASE_URL` to the `supabase_prod` environment using the `etl_runner` connection string.

After that, the ETL workflow is fully automated.

---

## Running the ETL

**Scheduled:** runs automatically on January 2nd each year.

**Manual trigger:** Actions → ETL → Run workflow. Specify a year range and optionally a comma-separated list of indicator codes to limit scope:

```
SP.POP.TOTL,NY.GDP.MKTP.CD,NY.GDP.PCAP.CD,SH.DYN.MORT,SE.ADT.LITR.ZS
```

**Locally:**

```bash
# Full run using .env values
python -m etl.pipeline

# Partial run overriding env vars inline
WB_START_YEAR=2020 WB_END_YEAR=2023 WB_INDICATOR_CODES=SP.POP.TOTL python -m etl.pipeline
```

Individual indicators that return API errors are skipped with a warning logged; the rest of the run continues. Skipped indicators are listed in the final log line.

---

## Adding a Migration

1. Generate a new timestamped file in `supabase/migrations/`:
   ```bash
   supabase migration new <description>
   ```
2. Write the DDL in the generated file.
3. If new tables are added, the `etl_runner` role inherits access automatically via the default privileges set in migration 6. No additional `GRANT` statements are needed unless the required permissions differ from `INSERT, UPDATE, SELECT`.
4. Test locally with `supabase db reset`, then open a PR. The CI workflow validates the migration before merge.
