import logging
import os
import sys

from dotenv import load_dotenv

from etl import extract, load, transform

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run(
    dsn: str,
    start_year: int,
    end_year: int,
    indicator_codes: list[str] | None = None,
    source_id: int = 2,
) -> None:
    conn = load.get_connection(dsn)
    try:
        logger.info("--- extract ---")
        countries  = extract.fetch_countries()
        indicators = extract.fetch_indicators(source_id=source_id)

        if indicator_codes:
            code_set   = set(indicator_codes)
            indicators = [i for i in indicators if i["indicator_code"] in code_set]
            logger.info("filtered to %d indicators", len(indicators))

        all_rows: list[dict] = []
        for idx, ind in enumerate(indicators, 1):
            code = ind["indicator_code"]
            logger.info("[%d/%d] fetching %s", idx, len(indicators), code)
            rows = extract.fetch_indicator_data(code, start_year, end_year)
            all_rows.extend(rows)

        logger.info("--- load staging (%d rows) ---", len(all_rows))
        load.truncate_staging(conn)
        load.insert_staging(conn, all_rows)

        logger.info("--- transform ---")
        transform.upsert_dim_countries(conn, countries)
        transform.upsert_dim_indicators(conn, indicators)
        transform.upsert_dim_dates(conn)
        transform.upsert_fact_wdi(conn)

        logger.info("pipeline complete")
    finally:
        conn.close()


def main() -> None:
    dsn        = os.environ["DATABASE_URL"]
    start_year = int(os.getenv("WB_START_YEAR", "2000"))
    end_year   = int(os.getenv("WB_END_YEAR",   "2023"))
    codes_raw  = os.getenv("WB_INDICATOR_CODES", "")
    indicator_codes = [c.strip() for c in codes_raw.split(",") if c.strip()] or None
    run(dsn, start_year, end_year, indicator_codes=indicator_codes)


if __name__ == "__main__":
    main()
