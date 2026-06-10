import logging
import time

import requests

BASE_URL = "https://api.worldbank.org/v2"
_PER_PAGE = 1000
_BACKOFF_SECS = 0.5

logger = logging.getLogger(__name__)


def _paginate(url: str, params: dict) -> list:
    records = []
    page = 1
    while True:
        resp = requests.get(url, params={**params, "page": page}, timeout=30)
        resp.raise_for_status()
        meta, page_records = resp.json()
        if not page_records:
            break
        records.extend(page_records)
        if page >= int(meta["pages"]):
            break
        page += 1
        time.sleep(_BACKOFF_SECS)
    return records


def fetch_countries() -> list[dict]:
    """Return all sovereign countries, excluding World Bank regional aggregates."""
    raw = _paginate(
        f"{BASE_URL}/country",
        {"format": "json", "per_page": _PER_PAGE},
    )
    countries = []
    for c in raw:
        # Aggregates (regions, income groups) have region.id == "NA"
        if c.get("region", {}).get("id") in ("NA", "", None):
            continue
        countries.append({
            "country_code": c["id"],
            "country_name": c["name"],
            "region":       c.get("region", {}).get("value"),
            "income_group": c.get("incomeLevel", {}).get("value"),
            "lending_type": c.get("lendingType", {}).get("value"),
            "capital_city": c.get("capitalCity") or None,
            "longitude":    float(c["longitude"]) if c.get("longitude") else None,
            "latitude":     float(c["latitude"])  if c.get("latitude")  else None,
        })
    logger.info("fetched %d countries", len(countries))
    return countries


def fetch_indicators(source_id: int = 2) -> list[dict]:
    """Return all indicators for a WB data source (2 = World Development Indicators)."""
    raw = _paginate(
        f"{BASE_URL}/indicator",
        {"format": "json", "per_page": _PER_PAGE, "source": source_id},
    )
    indicators = []
    for ind in raw:
        topic = ind["topics"][0].get("value") if ind.get("topics") else None
        indicators.append({
            "indicator_code": ind["id"],
            "indicator_name": ind["name"],
            "topic":          topic,
            "source_note":    ind.get("sourceNote") or None,
        })
    logger.info("fetched %d indicators", len(indicators))
    return indicators


def fetch_indicator_data(
    indicator_code: str,
    start_year: int,
    end_year: int,
) -> list[dict]:
    """Return all non-null country-year observations for a single indicator."""
    raw = _paginate(
        f"{BASE_URL}/country/all/indicator/{indicator_code}",
        {
            "format":   "json",
            "per_page": _PER_PAGE,
            "date":     f"{start_year}:{end_year}",
        },
    )
    rows = []
    for rec in raw:
        if rec.get("value") is None:
            continue
        iso3 = (rec.get("countryiso3code") or "").strip()
        if len(iso3) != 3:
            continue
        rows.append({
            "country_code":   iso3,
            "country_name":   rec["country"]["value"],
            "indicator_code": rec["indicator"]["id"],
            "indicator_name": rec["indicator"]["value"],
            "year":           int(rec["date"]),
            "value":          rec["value"],
            "unit":           rec.get("unit") or None,
            "obs_status":     rec.get("obs_status") or None,
        })
    return rows
