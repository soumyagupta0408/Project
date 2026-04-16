from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.alert import AlertLog


def _severity(aqi: float, threshold: int) -> str:
    excess = aqi - threshold
    if excess <= 50:  return "Low"
    if excess <= 150: return "Moderate"
    if excess <= 250: return "High"
    return "Severe"


def log_alert(db: Session, user_id: int, station: str, pollutant: str,
              aqi_value: float, threshold: int) -> AlertLog:
    alert = AlertLog(
        user_id=user_id,
        station=station,
        pollutant=pollutant,
        aqi_value=aqi_value,
        threshold=threshold,
        severity=_severity(aqi_value, threshold),
        message=(
            f"{pollutant} AQI of {aqi_value:.0f} at {station} "
            f"exceeded your threshold of {threshold}."
        ),
        triggered_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alerts_for_user(db: Session, user_id: int,
                        limit: int = 50, offset: int = 0) -> list:
    return (
        db.query(AlertLog)
        .filter(AlertLog.user_id == user_id)
        .order_by(desc(AlertLog.triggered_at))
        .offset(offset)
        .limit(limit)
        .all()
    )