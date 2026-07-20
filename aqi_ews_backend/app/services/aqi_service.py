"""
app/services/aqi_service.py

Data pipeline (in priority order):
  1. DB cache  — if fresh (< CACHE_TTL_MINUTES), return immediately.
  2. WAQI API  — primary live source (real-time, reliable).
  3. data.gov.in CPCB API — fallback when WAQI fails.

AQI Calculation:
  WAQI already returns a pre-computed AQI value (same CPCB standard).
  Individual pollutant sub-indices are also computed via official CPCB
  breakpoint tables for display purposes.
"""

from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio
import time
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import get_settings
from app.models.aqi_reading import AQIReading
from app.schemas.aqi import AQIResponse, PollutantReading, StationSummary, AllStationsResponse

settings = get_settings()

CACHE_TTL_MINUTES = 15  # WAQI updates hourly, 15 min cache is fine

# ── Data sources ───────────────────────────────────────────────────────────────
WAQI_URL = "https://api.waqi.info/feed/{station}/?token={token}"

CPCB_URL = (
    f"https://api.data.gov.in/resource/{settings.DATA_GOV_RESOURCE_ID}"
    f"?api-key={settings.DATA_GOV_API_KEY}&format=json&limit=2000"
)


# ══════════════════════════════════════════════════════════════════════════════
#  CPCB AQI BREAKPOINT TABLES  (National AQI, India)
#  Source: CPCB "National Air Quality Index" technical document.
#  Each tuple: (C_low, C_high, I_low, I_high)
# ══════════════════════════════════════════════════════════════════════════════

_BREAKPOINTS: dict[str, list[tuple]] = {
    "PM2.5": [
        (0,    30,    0,   50),
        (30,   60,   51,  100),
        (60,   90,  101,  200),
        (90,  120,  201,  300),
        (120, 250,  301,  400),
        (250, 500,  401,  500),
    ],
    "PM10": [
        (0,    50,    0,   50),
        (50,  100,   51,  100),
        (100, 250,  101,  200),
        (250, 350,  201,  300),
        (350, 430,  301,  400),
        (430, 600,  401,  500),
    ],
    "NO2": [
        (0,    40,    0,   50),
        (40,   80,   51,  100),
        (80,  180,  101,  200),
        (180, 280,  201,  300),
        (280, 400,  301,  400),
        (400, 800,  401,  500),
    ],
    "SO2": [
        (0,    40,    0,   50),
        (40,   80,   51,  100),
        (80,  380,  101,  200),
        (380, 800,  201,  300),
        (800, 1600, 301,  400),
        (1600, 2100, 401, 500),
    ],
    "CO": [
        (0,     1.0,   0,   50),
        (1.0,   2.0,  51,  100),
        (2.0,  10.0, 101,  200),
        (10.0, 17.0, 201,  300),
        (17.0, 34.0, 301,  400),
        (34.0, 50.0, 401,  500),
    ],
    "O3": [
        (0,    50,    0,   50),
        (50,  100,   51,  100),
        (100, 168,  101,  200),
        (168, 208,  201,  300),
        (208, 748,  301,  400),
        (748, 1000, 401,  500),
    ],
    "NH3": [
        (0,    200,   0,   50),
        (200,  400,  51,  100),
        (400,  800, 101,  200),
        (800, 1200, 201,  300),
        (1200, 1800, 301, 400),
        (1800, 2400, 401, 500),
    ],
    "PB": [
        (0,    0.5,   0,   50),
        (0.5,  1.0,  51,  100),
        (1.0,  2.0, 101,  200),
        (2.0,  3.0, 201,  300),
        (3.0,  3.5, 301,  400),
        (3.5,  5.0, 401,  500),
    ],
}

# WAQI key → canonical CPCB pollutant ID
_WAQI_KEY_MAP: dict[str, str] = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2":  "NO2",
    "so2":  "SO2",
    "co":   "CO",
    "o3":   "O3",
    "nh3":  "NH3",
}

_ALIASES: dict[str, str] = {
    "PM2.5": "PM2.5", "PM25": "PM2.5", "PM 2.5": "PM2.5",
    "PM10":  "PM10",  "PM 10": "PM10",
    "NO2":   "NO2",   "NO 2":  "NO2",
    "SO2":   "SO2",   "SO 2":  "SO2",
    "CO":    "CO",
    "O3":    "O3",    "O 3":   "O3",   "OZONE": "O3",
    "NH3":   "NH3",   "NH 3":  "NH3",
    "PB":    "PB",    "LEAD":  "PB",
}


# ══════════════════════════════════════════════════════════════════════════════
#  AQI FORMULA
# ══════════════════════════════════════════════════════════════════════════════

def _sub_index(raw_pollutant: str, concentration: float) -> float | None:
    key = _ALIASES.get(raw_pollutant.strip().upper())
    if key is None:
        return None
    c = concentration / 1000.0 if key == "CO" else concentration
    for (c_lo, c_hi, i_lo, i_hi) in _BREAKPOINTS[key]:
        if c_lo <= c <= c_hi:
            return i_lo + (i_hi - i_lo) / (c_hi - c_lo) * (c - c_lo)
    if c > _BREAKPOINTS[key][-1][1]:
        return 500.0
    return None


def compute_aqi(pollutant_avgs: dict[str, float]) -> float:
    sub_indices = [
        si for pid, conc in pollutant_avgs.items()
        if conc is not None
        for si in [_sub_index(pid, float(conc))]
        if si is not None
    ]
    return round(max(sub_indices), 1) if sub_indices else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _parse_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH — WAQI (primary)
# ══════════════════════════════════════════════════════════════════════════════

async def _fetch_from_waqi(city: str) -> tuple[list[dict], float | None] | None:
    """
    Fetch real-time data from WAQI API.
    Returns (records_list, waqi_aqi_value) or None on failure.
    Records are shaped like CPCB records for compatibility with cache layer.
    """
    token = getattr(settings, "WAQI_API_KEY", "") or ""
    station = getattr(settings, "WAQI_STATION", "") or ""

    if not token or not station:
        return None

    url = WAQI_URL.format(station=station, token=token)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url)
            r.raise_for_status()
            body = r.json()

        if body.get("status") != "ok":
            return None

        data = body["data"]
        waqi_aqi = float(data.get("aqi", 0)) or None

        # Timestamp from WAQI
        time_info = data.get("time", {})
        last_update = time_info.get("s", "")  # "2026-04-27 19:00:00"
        # Convert to UTC if tz offset present
        tz_str = time_info.get("tz", "+05:30")
        try:
            from datetime import timezone as tz
            import re
            sign = 1 if tz_str.startswith("+") else -1
            parts = re.findall(r"\d+", tz_str)
            offset = timedelta(hours=int(parts[0]), minutes=int(parts[1])) * sign
            local_dt = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
            utc_dt = local_dt - offset
            last_update_utc = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            last_update_utc = last_update

        iaqi = data.get("iaqi", {})
        station_name = data.get("city", {}).get("name", station)

        records = []
        for waqi_key, cpcb_id in _WAQI_KEY_MAP.items():
            if waqi_key in iaqi:
                value = _parse_float(iaqi[waqi_key].get("v"))
                if value is None:
                    continue
                # CO from WAQI is in mg/m³ * 1000 (µg/m³) — keep as µg/m³
                # Our _sub_index() divides CO by 1000 internally
                records.append({
                    "city":         city.title(),          # Fix Bug 1: was city.title (missing call)
                    "station":      station_name,
                    "pollutant_id": cpcb_id,               # Fix Bug 4: was hardcoded "AQI_FINAL"
                    "avg_value":    value,                 # Fix Bug 4: was waqi_aqi for every row
                    "min_value":    value,
                    "max_value":    value,
                    "unit":         "µg/m³",
                    "last_update":  last_update_utc,
                })

        # Store WAQI's pre-computed AQI as a special row so cache can return it
        if waqi_aqi:
            records.append({
                "city":         city.title(),
                "station":      station_name,
                "pollutant_id": "AQI_FINAL",
                "avg_value":    waqi_aqi,
                "min_value":    waqi_aqi,
                "max_value":    waqi_aqi,
                "unit":         "AQI",
                "last_update":  last_update_utc,
            })

        return (records, waqi_aqi) if records else None

    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH — data.gov.in CPCB (fallback)
# ══════════════════════════════════════════════════════════════════════════════

async def _fetch_from_cpcb(city: str) -> list[dict] | None:
    if not settings.DATA_GOV_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(CPCB_URL)
            r.raise_for_status()
            records = r.json().get("records", [])
        filtered = [
            rec for rec in records
            if str(rec.get("city", "")).strip().lower() == city.lower()
        ]
        # Reject stale data (older than 48 hours)
        fresh = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        for rec in filtered:
            raw_ts = str(rec.get("last_update", "")).strip()
            for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(raw_ts, fmt).replace(tzinfo=timezone.utc)
                    if dt >= cutoff:
                        fresh.append(rec)
                    break
                except ValueError:
                    continue
        return fresh or None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  DB CACHE LAYER
# ══════════════════════════════════════════════════════════════════════════════

def _cache_readings(db: Session, city: str, records: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    for rec in records:
        pollutant_id = str(rec.get("pollutant_id", "")).strip().upper()
        if not pollutant_id:
            continue

        recorded_at = now
        raw_ts = str(rec.get("last_update", "")).strip()
        if raw_ts:
            for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    recorded_at = datetime.strptime(raw_ts, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

        reading = AQIReading(
            city=city.title(),
            station=str(rec.get("station", "Unknown")).strip(),
            pollutant_id=pollutant_id,
            pollutant_min=_parse_float(rec.get("min_value")),
            pollutant_max=_parse_float(rec.get("max_value")),
            pollutant_avg=_parse_float(rec.get("avg_value")),
            unit=str(rec.get("unit", "µg/m³")).strip() or "µg/m³",
            recorded_at=recorded_at,
            fetched_at=now,
        )
        try:
            db.merge(reading)
        except Exception:
            db.rollback()

    try:
        db.commit()
    except Exception:
        db.rollback()


def _get_cached_readings(db: Session, city: str) -> list[AQIReading]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return (
        db.query(AQIReading)
        .filter(
            AQIReading.city == city.title(),
            AQIReading.recorded_at >= cutoff,
        )
        .order_by(desc(AQIReading.recorded_at))
        .all()
    )


def _cache_is_fresh(db: Session, city: str) -> bool:
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


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

async def get_aqi_for_city(db: Session, city: str = "indore") -> AQIResponse:
    """
    Priority chain:
      1. Fresh DB cache  → return immediately.
      2. WAQI API        → primary real-time source.
      3. data.gov.in     → fallback (may be stale; rejects data > 48h old).
      4. Stale DB cache  → best-effort.
      5. Empty           → frontend shows demo data.
    """
    city_title = city.strip().title()
    waqi_aqi: float | None = None

    # ── Only fetch from external APIs if cache is stale ───────────────────────
    cache_fresh = _cache_is_fresh(db, city_title)

    # If the cache is already fresh, the data was previously fetched from a
    # live source — mark it live immediately without re-fetching.
    live = cache_fresh

    if not cache_fresh:
        # ── Primary: WAQI ─────────────────────────────────────────────────────
        waqi_result = await _fetch_from_waqi(city_title)
        if waqi_result:
            records, waqi_aqi = waqi_result
            _cache_readings(db, city_title, records)
            live = True

        else:
            # ── Fallback: data.gov.in CPCB ────────────────────────────────────
            records = await _fetch_from_cpcb(city_title)
            if records:
                _cache_readings(db, city_title, records)
                live = True

    # ── Read latest readings from DB (most recent per pollutant only) ─────────
    cached = _get_cached_readings(db, city_title)

    if cached:
        # Use only the LATEST reading per pollutant (not 24h average)
        latest_per_pollutant: dict[str, AQIReading] = {}
        for r in cached:  # already ordered by recorded_at desc
            pid = str(r.pollutant_id).strip().upper()
            if pid not in latest_per_pollutant:
                latest_per_pollutant[pid] = r

        pollutant_avgs = {
            pid: r.pollutant_avg
            for pid, r in latest_per_pollutant.items()
            if r.pollutant_avg is not None
        }

        # Use WAQI's pre-computed AQI if available (most accurate),
        # otherwise compute from breakpoints using latest concentrations
        if waqi_aqi:
            aqi_index = waqi_aqi
        elif "AQI_FINAL" in latest_per_pollutant:
            aqi_index = latest_per_pollutant.pop("AQI_FINAL").pollutant_avg
        else:
            aqi_index = compute_aqi(pollutant_avgs)

        readings = [
            PollutantReading(
                pollutant_id=r.pollutant_id,
                pollutant_avg=r.pollutant_avg,
                pollutant_min=r.pollutant_min,
                pollutant_max=r.pollutant_max,
                unit=r.unit,
                station=r.station,
            )
            for r in latest_per_pollutant.values()
            if r.pollutant_id != "AQI_FINAL"
        ]

        return AQIResponse(
            city=city_title,
            readings=readings,
            aqi_index=aqi_index,
            live=live,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

    # Nothing in DB → frontend shows demo data
    return AQIResponse(
        city=city_title,
        readings=[],
        live=False,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ALL INDORE STATIONS — real CPCB data + primary WAQI station
# ══════════════════════════════════════════════════════════════════════════════

# Known CPCB monitoring stations in Indore with coordinates + WAQI slugs
_INDORE_STATION_META: dict[str, dict] = {
    "Chhoti Gwaltoli, Indore - MPPCB": {
        "short": "Chhoti Gwaltoli", "lat": 22.4310, "lon": 75.5213,
        "is_primary": True, "waqi_slug": "india/indore/chhoti-gwaltoli",
    },
    "Regional Park, Indore - IMC": {
        "short": "Regional Park", "lat": 22.6780, "lon": 75.8559,
        "is_primary": False, "waqi_slug": "india/indore/regional-park",
    },
    "Airport Area, Indore - IMC": {
        "short": "Airport Area", "lat": 22.7289, "lon": 75.8076,
        "is_primary": False, "waqi_slug": "india/indore/airport-area",
    },
    "Maguda Nagar, Indore - IMC": {
        "short": "Maguda Nagar", "lat": 22.7524, "lon": 75.8872,
        "is_primary": False, "waqi_slug": "india/indore/maguda-nagar",
    },
    "Residency Area, Indore - IMC": {
        "short": "Residency Area", "lat": 22.7084, "lon": 75.8815,
        "is_primary": False, "waqi_slug": "india/indore/residency-area",
    },
}


def _aqi_category(aqi: float) -> str:
    if aqi <= 50:  return "Good"
    if aqi <= 100: return "Satisfactory"
    if aqi <= 200: return "Moderate"
    if aqi <= 300: return "Poor"
    if aqi <= 400: return "Very Poor"
    return "Severe"


# ── In-memory cache for station data (avoids repeated slow API calls) ─────────
_stations_cache: dict = {"data": None, "ts": 0}
_STATIONS_CACHE_TTL = 300  # 5 minutes


async def _fetch_cpcb_indore() -> list[dict]:
    """Fetch CPCB records for Indore stations. Returns empty list on failure."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(CPCB_URL)
            r.raise_for_status()
            all_records = r.json().get("records", [])
        return [
            rec for rec in all_records
            if str(rec.get("city", "")).strip().lower() == "indore"
        ]
    except Exception:
        return []


async def _fetch_waqi_station(slug: str) -> tuple[float | None, str | None]:
    """Fetch AQI for a single WAQI station slug. Returns (aqi, dominant_pollutant)."""
    token = getattr(settings, "WAQI_API_KEY", "") or ""
    if not token:
        return None, None
    url = WAQI_URL.format(station=slug, token=token)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            body = r.json()
        if body.get("status") != "ok":
            return None, None
        data = body["data"]
        aqi = float(data.get("aqi", 0)) or None
        # Find dominant pollutant
        iaqi = data.get("iaqi", {})
        dominant = None
        if iaqi:
            poll_vals = {}
            for waqi_key, cpcb_id in _WAQI_KEY_MAP.items():
                if waqi_key in iaqi:
                    v = _parse_float(iaqi[waqi_key].get("v"))
                    if v is not None:
                        si = _sub_index(cpcb_id, v)
                        if si is not None:
                            poll_vals[cpcb_id] = si
            if poll_vals:
                dominant = max(poll_vals, key=poll_vals.get)
        return aqi, dominant
    except Exception:
        return None, None



async def get_all_indore_stations() -> AllStationsResponse:
    """
    Returns real AQI for every CPCB monitoring station in Indore.
    - Primary station (Chhoti Gwaltoli): fetched from WAQI (reliable, fast).
    - Other stations: fetched from CPCB data.gov.in (slow, may timeout).
    - If CPCB is unreachable, estimates are derived from primary AQI.
    Results are cached for 5 minutes.
    """
    # Return cached data if fresh
    if _stations_cache["data"] and (time.time() - _stations_cache["ts"]) < _STATIONS_CACHE_TTL:
        return _stations_cache["data"]

    now_str = datetime.now(timezone.utc).isoformat()
    last_upd = datetime.now(timezone.utc).strftime("%d-%m-%Y %H:%M:%S")

    # ── 1. Fetch primary from WAQI + try CPCB concurrently ────────────────────
    waqi_result, cpcb_records = await asyncio.gather(
        _fetch_from_waqi("Indore"),
        _fetch_cpcb_indore(),
    )

    primary_aqi: float | None = None
    primary_dominant: str | None = None
    if waqi_result:
        _, primary_aqi = waqi_result

    # ── 2. Try to extract other stations from CPCB data ───────────────────────
    station_pollutants: dict[str, dict[str, float]] = defaultdict(dict)
    station_last_update: dict[str, str] = {}
    for rec in cpcb_records:
        sname = str(rec.get("station", "")).strip()
        pid = str(rec.get("pollutant_id", "")).strip().upper()
        avg = _parse_float(rec.get("avg_value"))
        if sname and pid and avg is not None:
            station_pollutants[sname][pid] = avg
            station_last_update[sname] = str(rec.get("last_update", ""))

    # ── 3. Build station list ─────────────────────────────────────────────────
    stations: list[StationSummary] = []

    # Offsets for deriving estimates (percentage of primary AQI)
    # These represent typical spatial variation across Indore stations
    _ESTIMATE_OFFSETS = {
        "Regional Park":   -0.08,   # typically cleaner (park area)
        "Airport Area":    +0.05,   # slightly worse (traffic)
        "Maguda Nagar":    +0.12,   # industrial area, worse
        "Residency Area":  -0.05,   # residential, slightly better
    }

    for full_name, meta in _INDORE_STATION_META.items():
        is_primary = meta["is_primary"]
        short = meta["short"]

        if is_primary and primary_aqi is not None:
            aqi_val = round(primary_aqi, 1)
            data_src = "WAQI (real-time)"
            upd = last_upd
            dominant = None
        else:
            # Try CPCB data first
            poll_avgs = station_pollutants.get(full_name, {})
            if poll_avgs:
                aqi_val = round(compute_aqi(poll_avgs), 1)
                upd = station_last_update.get(full_name, last_upd)
                data_src = "CPCB"
                dominant = None
                sub_indices = {
                    pid: si for pid, conc in poll_avgs.items()
                    for si in [_sub_index(pid, float(conc))]
                    if si is not None
                }
                if sub_indices:
                    dominant = max(sub_indices, key=sub_indices.get)
            elif primary_aqi is not None:
                # Derive estimate from primary AQI
                offset = _ESTIMATE_OFFSETS.get(short, 0)
                aqi_val = round(primary_aqi * (1 + offset), 1)
                aqi_val = max(1, aqi_val)  # AQI can't be 0
                upd = last_upd
                data_src = "Estimated"
                dominant = None
            else:
                continue  # no data available at all

        stations.append(StationSummary(
            name=full_name,
            short_name=short,
            lat=meta["lat"],
            lon=meta["lon"],
            aqi=aqi_val,
            category=_aqi_category(aqi_val),
            dominant=dominant,
            last_update=upd,
            is_primary=is_primary,
            data_source=data_src,
        ))

    # Sort cleanest first
    stations.sort(key=lambda s: s.aqi if s.aqi is not None else 9999)

    result = AllStationsResponse(
        city="Indore",
        primary_aqi=round(primary_aqi, 1) if primary_aqi else None,
        stations=stations,
        fetched_at=now_str,
    )

    # Cache the result
    if stations:
        _stations_cache["data"] = result
        _stations_cache["ts"] = time.time()

    return result

