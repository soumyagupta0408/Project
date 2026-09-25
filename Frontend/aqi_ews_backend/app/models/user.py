"""
app/models/user.py
SQLAlchemy ORM model for the `users` table.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Identity
    full_name: Mapped[str]          = mapped_column(String(120), nullable=False)
    email: Mapped[str | None]       = mapped_column(String(180), unique=True, nullable=True, index=True)
    phone: Mapped[str | None]       = mapped_column(String(15),  unique=True, nullable=True, index=True)
    hashed_password: Mapped[str]    = mapped_column(String(255), nullable=False)

    # Location (stored from GPS or manual entry)
    address: Mapped[str | None]     = mapped_column(Text,         nullable=True)
    latitude: Mapped[str | None]    = mapped_column(String(20),   nullable=True)
    longitude: Mapped[str | None]   = mapped_column(String(20),   nullable=True)

    # Preferences
    alert_threshold: Mapped[int]    = mapped_column(default=150)   # AQI threshold for notifications
    is_active: Mapped[bool]         = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime]    = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime]    = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} phone={self.phone}>"
