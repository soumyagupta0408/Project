"""Initial migration — create users, alert_logs, aqi_readings tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column("full_name",       sa.String(120),   nullable=False),
        sa.Column("email",           sa.String(180),   nullable=True,  unique=True),
        sa.Column("phone",           sa.String(15),    nullable=True,  unique=True),
        sa.Column("hashed_password", sa.String(255),   nullable=False),
        sa.Column("address",         sa.Text(),        nullable=True),
        sa.Column("latitude",        sa.String(20),    nullable=True),
        sa.Column("longitude",       sa.String(20),    nullable=True),
        sa.Column("alert_threshold", sa.Integer(),     nullable=False, server_default="150"),
        sa.Column("is_active",       sa.Boolean(),     nullable=False, server_default=sa.true()),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_phone", "users", ["phone"])

    # ── alert_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "alert_logs",
        sa.Column("id",           sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id",      sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("station",      sa.String(120), nullable=False),
        sa.Column("pollutant",    sa.String(20),  nullable=False),
        sa.Column("aqi_value",    sa.Float(),     nullable=False),
        sa.Column("threshold",    sa.Integer(),   nullable=False),
        sa.Column("severity",     sa.String(20),  nullable=False),
        sa.Column("message",      sa.Text(),      nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alert_logs_user_id",     "alert_logs", ["user_id"])
    op.create_index("ix_alert_logs_triggered_at","alert_logs", ["triggered_at"])

    # ── aqi_readings ──────────────────────────────────────────────────────────
    op.create_table(
        "aqi_readings",
        sa.Column("id",             sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city",           sa.String(80),  nullable=False),
        sa.Column("station",        sa.String(160), nullable=False),
        sa.Column("pollutant_id",   sa.String(20),  nullable=False),
        sa.Column("pollutant_min",  sa.Float(),     nullable=True),
        sa.Column("pollutant_max",  sa.Float(),     nullable=True),
        sa.Column("pollutant_avg",  sa.Float(),     nullable=True),
        sa.Column("unit",           sa.String(20),  nullable=True),
        sa.Column("recorded_at",    sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at",     sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("city", "station", "pollutant_id", "recorded_at",
                            name="uq_reading"),
    )
    op.create_index("ix_aqi_readings_city",       "aqi_readings", ["city"])
    op.create_index("ix_aqi_readings_recorded_at","aqi_readings", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("aqi_readings")
    op.drop_table("alert_logs")
    op.drop_table("users")
