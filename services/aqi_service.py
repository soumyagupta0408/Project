"""
app/services/aqi_service.py
Fetches AQI data from data.gov.in CPCB API and caches results in MySQL.
Falls back to the most recent cached rows when the API is unavailable.
"""
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import get_settings
from app.models.aqi_reading import AQIReading
from app.schemas.aqi import AQIResponse, PollutantReading

settings = get_settings()

CPCB_URL = (
    f"https://api.data.gov.in/resource/{settings.DATA_GOV_RESOURCE_ID}"
    f"?api-key={settings.DATA_GOV_API_KEY}&format=json&limit=500"
)
CACHE_TTL_MINUTES = 5   # only re-fetch if cache is older than this


def _parse_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


async def _fetch_from_cpcb(city: str) -> list[dict] | None:
    """
    Calls the data.gov.in CPCB endpoint.
    Returns a list of raw record dicts for the requested city, or None on error.
    """
    if not settings.DATA_GOV_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(CPCB_URL)
            r.raise_for_status()
            records = r.json().get("records", [])
        return [
            rec for rec in records
            if str(rec.get("city", "")).strip().lower() == city.lower()
        ]
    except Exception:
        return None


def _cache_readings(db: Session, city: str, records: list[dict]) -> None:
    """Persist fresh CPCB records to the aqi_readings table."""
    now = datetime.now(timezone.utc)
    for rec in records:
        pollutant_id = str(rec.get("pollutant_id", "")).strip().upper()
        if not pollutant_id:
            continue

        # Use last_update from API if present, else now
        try:
            recorded_at = datetime.fromisoformat(str(rec.get("last_update", ""))).replace(tzinfo=timezone.utc)
        except Exception:
            recorded_at = now

        reading = AQIReading(
            city=city.title(),
            station=str(rec.get("station", "Unknown")).strip(),
            pollutant_id=pollutant_id,
            pollutant_min=_parse_float(rec.get("pollutant_min")),
            pollutant_max=_parse_float(rec.get("pollutant_max")),
            pollutant_avg=_parse_float(rec.get("pollutant_avg")),
            unit=str(rec.get("unit", "µg/m³")).strip() or "µg/m³",
            recorded_at=recorded_at,
            fetched_at=now,
        )
        # Ignore duplicate key violations gracefully
        try:
            db.merge(reading)
        except Exception:
            db.rollback()

    try:
        db.commit()
    except Exception:
        db.rollback()


def _get_cached_readings(db: Session, city: str) -> list[AQIReading]:
    """Return the latest set of cached readings for a city."""
    subq = (
        db.query(
            AQIReading.pollutant_id,
            AQIReading.station,
            AQIReading.fetched_at,
        )
        .filter(AQIReading.city == city.title())
        .order_by(desc(AQIReading.fetched_at))
        .subquery()
    )
    return (
        db.query(AQIReading)
        .filter(
            AQIReading.city == city.title(),
        )
        .order_by(desc(AQIReading.fetched_at))
        .limit(50)
        .all()
    )


def _cache_is_fresh(db: Session, city: str) -> bool:
    """Returns True if the most recent cache entry is within TTL."""
    latest = (
        db.query(AQIReading.fetched_at)
        .filter(AQIReading.city == city.title())
        .order_by(desc(AQIReading.fetched_at))
        .first()
    )
    if not latest:
        return False
    age = datetime.now(timezone.utc) - latest.fetched_at.replace(tzinfo=timezone.utc)
    return age < timedelta(minutes=CACHE_TTL_MINUTES)


async def get_aqi_for_city(db: Session, city: str = "indore") -> AQIResponse:
    """
    Main entry-point for the /api/aqi/{city} route.
    1. If DB cache is fresh → return cache.
    2. Else → fetch from CPCB → cache in DB → return.
    3. If CPCB fails → return stale cache (best-effort).
    """
    city_title = city.strip().title()

    # ── Try live API if cache is stale ───────────────────────────────────────
    live = False
    if not _cache_is_fresh(db, city_title):
        records = await _fetch_from_cpcb(city_title)
        if records:
            _cache_readings(db, city_title, records)
            live = True

    # ── Read from DB cache ────────────────────────────────────────────────────
    cached = _get_cached_readings(db, city_title)

    if cached:
        readings = [
            PollutantReading(
                pollutant_id=r.pollutant_id,
                pollutant_avg=r.pollutant_avg,
                pollutant_min=r.pollutant_min,
                pollutant_max=r.pollutant_max,
                unit=r.unit,
                station=r.station,
            )
            for r in cached
        ]
        return AQIResponse(
            city=city_title,
            readings=readings,
            live=live,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

    # ── No data at all → return empty (frontend shows mock) ──────────────────
    return AQIResponse(
        city=city_title,
        readings=[],
        live=False,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
