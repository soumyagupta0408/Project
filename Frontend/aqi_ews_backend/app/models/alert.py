"""
app/models/alert.py
Stores AQI threshold breach events per user.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int]          = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int]     = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    station: Mapped[str]     = mapped_column(String(120), nullable=False)
    pollutant: Mapped[str]   = mapped_column(String(20),  nullable=False)
    aqi_value: Mapped[float] = mapped_column(Float,       nullable=False)
    threshold: Mapped[int]   = mapped_column(Integer,     nullable=False)
    severity: Mapped[str]    = mapped_column(String(20),  nullable=False)   # Low | Moderate | High | Severe
    message: Mapped[str | None] = mapped_column(Text,     nullable=True)

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationship back to user
    user = relationship("User", backref="alerts")

    def __repr__(self) -> str:
        return f"<AlertLog id={self.id} user={self.user_id} aqi={self.aqi_value}>"
