import logging

import psycopg2.extras

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


def upsert_dim_countries(conn, countries: list[dict]) -> None:
    sql = """
        INSERT INTO public.dim_country
            (country_code, country_name, region, income_group, lending_type,
             capital_city, longitude, latitude)
        VALUES %s
        ON CONFLICT (country_code) DO UPDATE SET
            country_name = EXCLUDED.country_name,
            region       = EXCLUDED.region,
            income_group = EXCLUDED.income_group,
            lending_type = EXCLUDED.lending_type,
            capital_city = EXCLUDED.capital_city,
            longitude    = EXCLUDED.longitude,
            latitude     = EXCLUDED.latitude,
            updated_at   = now()
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            sql,
            [
                (
                    c["country_code"], c["country_name"], c["region"],
                    c["income_group"], c["lending_type"], c["capital_city"],
                    c["longitude"], c["latitude"],
                )
                for c in countries
            ],
            page_size=_BATCH_SIZE,
        )
    conn.commit()
    logger.info("upserted %d rows into dim_country", len(countries))


def upsert_dim_indicators(conn, indicators: list[dict]) -> None:
    sql = """
        INSERT INTO public.dim_indicator
            (indicator_code, indicator_name, topic, source_note)
        VALUES %s
        ON CONFLICT (indicator_code) DO UPDATE SET
            indicator_name = EXCLUDED.indicator_name,
            topic          = EXCLUDED.topic,
            source_note    = EXCLUDED.source_note,
            updated_at     = now()
    """
    with conn.cursor() as cur:
        for i in range(0, len(indicators), _BATCH_SIZE):
            batch = indicators[i : i + _BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                sql,
                [
                    (
                        ind["indicator_code"], ind["indicator_name"],
                        ind["topic"], ind["source_note"],
                    )
                    for ind in batch
                ],
            )
    conn.commit()
    logger.info("upserted %d rows into dim_indicator", len(indicators))


def upsert_dim_dates(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO public.dim_date (year)
            SELECT DISTINCT year FROM staging.stg_wdi_raw
            ORDER BY year
            ON CONFLICT (year) DO NOTHING
        """)
    conn.commit()


def upsert_fact_wdi(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO public.fact_wdi
                (country_key, indicator_key, date_key, value, obs_status)
            SELECT
                dc.country_key,
                di.indicator_key,
                dd.date_key,
                s.value,
                s.obs_status
            FROM  staging.stg_wdi_raw  s
            JOIN  public.dim_country   dc ON dc.country_code   = s.country_code
            JOIN  public.dim_indicator di ON di.indicator_code = s.indicator_code
            JOIN  public.dim_date      dd ON dd.year           = s.year
            ON CONFLICT (country_key, indicator_key, date_key) DO UPDATE SET
                value      = EXCLUDED.value,
                obs_status = EXCLUDED.obs_status,
                loaded_at  = now()
        """)
        count = cur.rowcount
    conn.commit()
    logger.info("upserted %d rows into fact_wdi", count)
    return count
