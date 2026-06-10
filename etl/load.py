import logging

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10_000


def get_connection(dsn: str):
    return psycopg2.connect(dsn)


def truncate_staging(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE staging.stg_wdi_raw")
    conn.commit()


def insert_staging(conn, rows: list[dict]) -> int:
    if not rows:
        return 0
    sql = """
        INSERT INTO staging.stg_wdi_raw
            (country_code, country_name, indicator_code, indicator_name,
             year, value, unit, obs_status)
        VALUES %s
    """
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), _BATCH_SIZE):
            batch = rows[i : i + _BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                sql,
                [
                    (
                        r["country_code"], r["country_name"],
                        r["indicator_code"], r["indicator_name"],
                        r["year"], r["value"], r["unit"], r["obs_status"],
                    )
                    for r in batch
                ],
            )
            total += len(batch)
    conn.commit()
    logger.info("inserted %d rows into staging.stg_wdi_raw", total)
    return total
