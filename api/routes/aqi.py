"""
app/api/routes/aqi.py
GET  /api/aqi/{city}         — fetch latest AQI readings (cached in DB)
GET  /api/aqi/{city}/history — last N cached readings from DB
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.schemas.aqi import AQIResponse, PollutantReading
from app.services.aqi_service import get_aqi_for_city
from app.models.aqi_reading import AQIReading
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/aqi", tags=["aqi"])


@router.get("/{city}", response_model=AQIResponse)
async def aqi_city(
    city: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),   # require auth
):
    """
    Returns the latest AQI readings for the given city.
    Serves from the MySQL cache when data is fresh (<5 min old);
    otherwise fetches from the CPCB API, caches, then returns.
    """
    return await get_aqi_for_city(db, city)


@router.get("/{city}/history", response_model=list[PollutantReading])
def aqi_history(
    city: str,
    pollutant: str | None = Query(None, description="Filter by pollutant, e.g. PM2.5"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Returns historical cached readings for a city from the DB.
    Optionally filtered by pollutant_id.
    """
    query = (
        db.query(AQIReading)
        .filter(AQIReading.city == city.strip().title())
    )
    if pollutant:
        query = query.filter(AQIReading.pollutant_id == pollutant.upper())

    rows = query.order_by(desc(AQIReading.recorded_at)).limit(limit).all()

    return [
        PollutantReading(
            pollutant_id=r.pollutant_id,
            pollutant_avg=r.pollutant_avg,
            pollutant_min=r.pollutant_min,
            pollutant_max=r.pollutant_max,
            unit=r.unit,
            station=r.station,
        )
        for r in rows
    ]
