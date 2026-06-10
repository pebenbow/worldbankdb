import pytest

pytestmark = pytest.mark.schema


@pytest.mark.parametrize("schema,table", [
    ("staging", "stg_wdi_raw"),
    ("public",  "dim_country"),
    ("public",  "dim_indicator"),
    ("public",  "dim_date"),
    ("public",  "fact_wdi"),
])
def test_table_exists(cur, schema, table):
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
    """, (schema, table))
    assert cur.fetchone()[0] == 1, f"{schema}.{table} not found"


@pytest.mark.parametrize("schema,table,column", [
    ("public",  "dim_country",   "country_code"),
    ("public",  "dim_country",   "region"),
    ("public",  "dim_country",   "income_group"),
    ("public",  "dim_indicator", "indicator_code"),
    ("public",  "dim_indicator", "topic"),
    ("public",  "dim_date",      "year"),
    ("public",  "dim_date",      "decade"),
    ("public",  "dim_date",      "century"),
    ("public",  "fact_wdi",      "country_key"),
    ("public",  "fact_wdi",      "indicator_key"),
    ("public",  "fact_wdi",      "date_key"),
    ("public",  "fact_wdi",      "value"),
    ("public",  "fact_wdi",      "obs_status"),
    ("staging", "stg_wdi_raw",   "country_code"),
    ("staging", "stg_wdi_raw",   "indicator_code"),
    ("staging", "stg_wdi_raw",   "year"),
    ("staging", "stg_wdi_raw",   "value"),
    ("staging", "stg_wdi_raw",   "loaded_at"),
])
def test_column_exists(cur, schema, table, column):
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
    """, (schema, table, column))
    assert cur.fetchone()[0] == 1, f"Column {schema}.{table}.{column} not found"


def test_dim_date_has_generated_columns(cur):
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'dim_date'
          AND column_name IN ('decade', 'century')
          AND is_generated = 'ALWAYS'
    """)
    assert cur.fetchone()[0] == 2


def test_fact_wdi_unique_constraint(cur):
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_schema    = 'public'
          AND table_name      = 'fact_wdi'
          AND constraint_type = 'UNIQUE'
    """)
    assert cur.fetchone()[0] >= 1


def test_fact_wdi_foreign_key_count(cur):
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_schema    = 'public'
          AND table_name      = 'fact_wdi'
          AND constraint_type = 'FOREIGN KEY'
    """)
    assert cur.fetchone()[0] == 3


def test_dim_country_unique_constraint(cur):
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_schema    = 'public'
          AND table_name      = 'dim_country'
          AND constraint_type = 'UNIQUE'
    """)
    assert cur.fetchone()[0] >= 1


def test_staging_lookup_index_exists(cur):
    cur.execute("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE schemaname = 'staging'
          AND tablename  = 'stg_wdi_raw'
          AND indexname  = 'idx_stg_wdi_raw_lookup'
    """)
    assert cur.fetchone()[0] == 1


@pytest.mark.parametrize("indexname", [
    "idx_fact_wdi_country",
    "idx_fact_wdi_indicator",
    "idx_fact_wdi_date",
])
def test_fact_wdi_indexes_exist(cur, indexname):
    cur.execute("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename  = 'fact_wdi'
          AND indexname  = %s
    """, (indexname,))
    assert cur.fetchone()[0] == 1, f"Index {indexname} not found"
