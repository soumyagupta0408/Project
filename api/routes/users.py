"""
app/api/routes/users.py
PATCH /api/users/me/threshold  — update alert threshold
GET   /api/users/me/alerts     — fetch user's alert log
POST  /api/users/me/alerts     — manually log an alert (called by dashboard)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import UserOut
from app.schemas.aqi import AlertLogOut, AlertThresholdUpdate
from app.services import user_service, alert_service
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.patch("/me/threshold", response_model=UserOut)
def update_threshold(
    body: AlertThresholdUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the AQI alert threshold for the logged-in user."""
    updated = user_service.update_alert_threshold(db, current_user.id, body.threshold)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    return updated


@router.get("/me/alerts", response_model=list[AlertLogOut])
def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch the alert history for the logged-in user."""
    return alert_service.get_alerts_for_user(db, current_user.id, limit, offset)


class AlertCreateRequest(AlertThresholdUpdate):
    station: str
    pollutant: str
    aqi_value: float
    threshold: int


from pydantic import BaseModel

class AlertCreate(BaseModel):
    station: str
    pollutant: str
    aqi_value: float


@router.post("/me/alerts", response_model=AlertLogOut, status_code=status.HTTP_201_CREATED)
def create_alert(
    body: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called by the Streamlit dashboard when a threshold breach is detected.
    Logs the event into the DB for the alert history tab.
    """
    alert = alert_service.log_alert(
        db=db,
        user_id=current_user.id,
        station=body.station,
        pollutant=body.pollutant,
        aqi_value=body.aqi_value,
        threshold=current_user.alert_threshold,
    )
    return alert
