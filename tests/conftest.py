import os

import psycopg2
import pytest


@pytest.fixture(scope="session")
def db_conn():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    yield conn
    conn.close()


@pytest.fixture
def cur(db_conn):
    with db_conn.cursor() as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def seed(db_conn):
    """Insert minimal test fixtures once for the session.

    Uses codes (ZZZ, ZZ.TEST.*) that won't collide with real WDI data.
    Staging rows for year 2022 are intentionally left in place for the
    idempotency test in test_data_quality.py.
    """
    with db_conn.cursor() as c:
        c.execute("""
            INSERT INTO public.dim_country
                (country_code, country_name, region, income_group)
            VALUES ('ZZZ', 'Test Country', 'Test Region', 'Test Income')
            ON CONFLICT (country_code) DO NOTHING
        """)
        c.execute("""
            INSERT INTO public.dim_indicator
                (indicator_code, indicator_name, topic)
            VALUES
                ('ZZ.TEST.1', 'Test Indicator One', 'Test'),
                ('ZZ.TEST.2', 'Test Indicator Two', 'Test')
            ON CONFLICT (indicator_code) DO NOTHING
        """)
        c.execute("""
            INSERT INTO public.dim_date (year)
            VALUES (2020), (2021)
            ON CONFLICT (year) DO NOTHING
        """)
        c.execute("""
            INSERT INTO public.fact_wdi
                (country_key, indicator_key, date_key, value)
            SELECT dc.country_key, di.indicator_key, dd.date_key,
                   (dd.year - 2000) * 10.0
            FROM  public.dim_country   dc
            CROSS JOIN public.dim_indicator di
            CROSS JOIN public.dim_date      dd
            WHERE  dc.country_code    = 'ZZZ'
              AND  di.indicator_code IN ('ZZ.TEST.1', 'ZZ.TEST.2')
              AND  dd.year           IN (2020, 2021)
            ON CONFLICT (country_key, indicator_key, date_key) DO NOTHING
        """)
        c.execute("""
            INSERT INTO staging.stg_wdi_raw
                (country_code, country_name, indicator_code, indicator_name, year, value)
            VALUES
                ('ZZZ', 'Test Country', 'ZZ.TEST.1', 'Test Indicator One', 2022, 220.0),
                ('ZZZ', 'Test Country', 'ZZ.TEST.2', 'Test Indicator Two', 2022, 230.0)
        """)
    db_conn.commit()
    yield
