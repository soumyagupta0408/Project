"""
app/schemas/aqi.py

Pydantic schemas for AQI API responses.

CHANGES vs previous version:
  - AQIResponse gains  `aqi_index`  (float | None) — computed by the service
    using official CPCB breakpoint tables instead of the old * 1.5 shortcut.
  - AQIResponse gains  `threshold`  (int) — system alert threshold returned
    to the frontend so it can draw the warning line correctly.
"""

from pydantic import BaseModel
from typing import Optional
from app.schemas.alert import AlertLogOut, AlertThresholdUpdate


class PollutantReading(BaseModel):
    pollutant_id:  str
    pollutant_avg: Optional[float] = None
    pollutant_min: Optional[float] = None
    pollutant_max: Optional[float] = None
    unit:          Optional[str]   = "µg/m³"
    station:       Optional[str]   = None

    class Config:
        from_attributes = True   # SQLAlchemy ORM → Pydantic (replaces orm_mode)


class AQIResponse(BaseModel):
    city:        str
    readings:    list[PollutantReading] = []

    # ── New fields ────────────────────────────────────────────────────────────
    # aqi_index: the overall AQI computed from CPCB breakpoint tables.
    # The frontend reads this directly: data.get("aqi_index")
    aqi_index:   Optional[float] = None

    # threshold: the system alert level. Frontend uses data.get("threshold", 150).
    # 100 = "Satisfactory" boundary on CPCB scale — good default for India.
    threshold:   int             = 100

    # ─────────────────────────────────────────────────────────────────────────
    live:        bool            = False
    fetched_at:  Optional[str]   = None


# ── Multi-station schemas ─────────────────────────────────────────────────────

class StationSummary(BaseModel):
    """AQI summary for a single monitoring station."""
    name:        str
    short_name:  str                  # display name without "- MPPCB" etc.
    lat:         float
    lon:         float
    aqi:         Optional[float] = None
    category:    Optional[str]   = None   # Good / Satisfactory / Moderate / …
    dominant:    Optional[str]   = None   # dominant pollutant
    last_update: Optional[str]   = None
    is_primary:  bool            = False  # True for the WAQI (real-time) station
    data_source: str             = "CPCB"


class AllStationsResponse(BaseModel):
    """All Indore monitoring stations with their latest AQI."""
    city:           str
    primary_aqi:    Optional[float] = None   # live AQI from primary WAQI station
    stations:       list[StationSummary] = []
    fetched_at:     Optional[str]  = None