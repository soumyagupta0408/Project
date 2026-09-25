"""
app/models/aqi_reading.py
Caches raw CPCB pollutant readings in the DB to avoid hammering the API.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AQIReading(Base):
    __tablename__ = "aqi_readings"
    __table_args__ = (
        UniqueConstraint("city", "station", "pollutant_id", "recorded_at", name="uq_reading"),
    )

    id: Mapped[int]               = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str]             = mapped_column(String(80), index=True)
    station: Mapped[str]          = mapped_column(String(160))
    pollutant_id: Mapped[str]     = mapped_column(String(20))   # PM2.5, PM10, NO2 …
    pollutant_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    pollutant_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    pollutant_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None]      = mapped_column(String(20),  nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    fetched_at: Mapped[datetime]  = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<AQIReading {self.city} {self.pollutant_id}={self.pollutant_avg}>"
