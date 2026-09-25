"""
app/api/routes/aqi.py
GET  /api/aqi/indore/stations — all Indore stations with real AQI
GET  /api/aqi/{city}          — fetch latest AQI readings (cached in DB)
GET  /api/aqi/{city}/history  — last N cached readings from DB
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.session import get_db
from app.schemas.aqi import AQIResponse, PollutantReading, AllStationsResponse
from app.services.aqi_service import get_aqi_for_city, get_all_indore_stations
from app.models.aqi_reading import AQIReading

router = APIRouter(prefix="/api/aqi", tags=["aqi"])


@router.get("/indore/stations", response_model=AllStationsResponse)
async def aqi_indore_stations():
    """
    Returns real-time AQI for all CPCB monitoring stations in Indore.
    - Chhoti Gwaltoli: sourced from WAQI (live, updates hourly).
    - All others: sourced from CPCB data.gov.in API.
    Public endpoint — no authentication required.
    """
    return await get_all_indore_stations()


@router.get("/{city}", response_model=AQIResponse)
async def aqi_city(
    city: str,
    db: Session = Depends(get_db),
):
    """
    Returns the latest AQI readings for the given city.
    Serves from the MySQL cache when data is fresh (<15 min old);
    otherwise fetches from the CPCB API, caches, then returns.
    Public endpoint — no authentication required.
    """
    return await get_aqi_for_city(db, city)


@router.get("/{city}/history", response_model=list[PollutantReading])
def aqi_history(
    city: str,
    pollutant: str | None = Query(None, description="Filter by pollutant, e.g. PM2.5"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Returns last N cached AQI readings for the given city from the DB.
    Public endpoint — no authentication required.
    """
    q = db.query(AQIReading).filter(
        AQIReading.city.ilike(city)
    )
    if pollutant:
        q = q.filter(AQIReading.pollutant_id == pollutant)
    return q.order_by(desc(AQIReading.recorded_at)).limit(limit).all()
