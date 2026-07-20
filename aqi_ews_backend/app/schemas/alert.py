from pydantic import BaseModel
from datetime import datetime


class AlertThresholdUpdate(BaseModel):
    threshold: int


class AlertLogOut(BaseModel):
    id: int
    user_id: int
    station: str
    pollutant: str
    aqi_value: float
    threshold: int
    created_at: datetime

    model_config = {"from_attributes": True}