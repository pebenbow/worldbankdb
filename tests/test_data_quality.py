"""
Data quality invariants and ELT integration tests.

The seed fixture in conftest.py inserts test countries/indicators/dates/facts
and two staging rows for year 2022 (not yet promoted to facts). Tests here
exercise both invariants on existing data and the transform pipeline itself.
"""

import pytest

from etl.transform import upsert_dim_dates, upsert_fact_wdi

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("seed")]


def test_fact_wdi_grain_is_unique(cur):
    """No two fact rows share the same (country, indicator, date) triplet."""
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT country_key, indicator_key, date_key
            FROM   public.fact_wdi
            GROUP  BY country_key, indicator_key, date_key
            HAVING COUNT(*) > 1
        ) dups
    """)
    assert cur.fetchone()[0] == 0


def test_fact_wdi_fully_joinable_to_dims(cur):
    """Every fact row has a valid match in all three dimension tables."""
    cur.execute("""
        SELECT COUNT(*) FROM public.fact_wdi f
        JOIN public.dim_country   dc ON dc.country_key   = f.country_key
        JOIN public.dim_indicator di ON di.indicator_key = f.indicator_key
        JOIN public.dim_date      dd ON dd.date_key      = f.date_key
    """)
    joined = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM public.fact_wdi")
    total = cur.fetchone()[0]

    assert joined == total


def test_dim_country_code_is_iso3(cur):
    """All country codes are exactly 3 uppercase alphabetic characters."""
    cur.execute(r"""
        SELECT COUNT(*) FROM public.dim_country
        WHERE country_code !~ '^[A-Z]{3}$'
    """)
    assert cur.fetchone()[0] == 0


def test_dim_date_decade_is_correct(cur):
    """dim_date.decade matches the expected integer arithmetic."""
    cur.execute("""
        SELECT COUNT(*) FROM public.dim_date
        WHERE decade != (year / 10) * 10
    """)
    assert cur.fetchone()[0] == 0


def test_dim_date_century_is_correct(cur):
    """dim_date.century matches the expected integer arithmetic."""
    cur.execute("""
        SELECT COUNT(*) FROM public.dim_date
        WHERE century != (year / 100) * 100
    """)
    assert cur.fetchone()[0] == 0


def test_seeded_facts_have_expected_values(cur):
    """Spot-check seeded values: year=2020 → value=200.0, year=2021 → value=210.0."""
    cur.execute("""
        SELECT dd.year, f.value
        FROM   public.fact_wdi      f
        JOIN   public.dim_country   dc ON dc.country_key   = f.country_key
        JOIN   public.dim_indicator di ON di.indicator_key = f.indicator_key
        JOIN   public.dim_date      dd ON dd.date_key      = f.date_key
        WHERE  dc.country_code   = 'ZZZ'
          AND  di.indicator_code = 'ZZ.TEST.1'
          AND  dd.year IN (2020, 2021)
        ORDER  BY dd.year
    """)
    rows = cur.fetchall()
    assert rows == [(2020, 200.0), (2021, 210.0)]


def test_staging_to_fact_upsert_is_idempotent(db_conn):
    """
    Running upsert_dim_dates + upsert_fact_wdi twice against the same staging
    data produces the same row count both times (ON CONFLICT DO UPDATE).

    The seed fixture leaves two staging rows for ZZZ/2022 that are not yet
    in fact_wdi; this test promotes them and then confirms a second pass
    doesn't create duplicates.
    """
    def fact_count_for_year(year):
        with db_conn.cursor() as c:
            c.execute("""
                SELECT COUNT(*) FROM public.fact_wdi
                WHERE date_key = (
                    SELECT date_key FROM public.dim_date WHERE year = %s
                )
            """, (year,))
            return c.fetchone()[0]

    # First pass: 2022 not yet in dim_date or fact_wdi
    upsert_dim_dates(db_conn)
    upsert_fact_wdi(db_conn)
    count_first = fact_count_for_year(2022)

    assert count_first == 2  # ZZZ × ZZ.TEST.1 + ZZZ × ZZ.TEST.2

    # Second pass: same staging rows, should produce no new facts
    upsert_dim_dates(db_conn)
    upsert_fact_wdi(db_conn)
    count_second = fact_count_for_year(2022)

    assert count_second == count_first
