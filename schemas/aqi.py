from datetime import datetime
from pydantic import BaseModel


class PollutantReading(BaseModel):
    pollutant_id: str
    pollutant_avg: float | None
    pollutant_min: float | None
    pollutant_max: float | None
    unit: str | None = "µg/m³"
    station: str


class AQIResponse(BaseModel):
    city: str
    readings: list[PollutantReading]
    live: bool
    fetched_at: str


class AlertLogOut(BaseModel):
    id: int
    station: str
    pollutant: str
    aqi_value: float
    threshold: int
    severity: str
    message: str | None
    triggered_at: datetime

    model_config = {"from_attributes": True}


class AlertThresholdUpdate(BaseModel):
    threshold: int