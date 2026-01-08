"""Add forecast tables.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-03

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create windgenerationforecast table
    op.create_table(
        "windgenerationforecast",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wind_farm_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("forecast_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "generation",
            sa.Float(),
            nullable=False,
            comment="Forecasted power generation in kW",
        ),
        sa.Column(
            "granularity",
            sa.Enum(
                "min_1",
                "min_5",
                "min_15",
                "min_30",
                "min_60",
                name="granularityenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "wind_speed",
            sa.Float(),
            nullable=True,
            comment="Forecasted wind speed in m/s",
        ),
        sa.Column(
            "wind_direction",
            sa.Float(),
            nullable=True,
            comment="Forecasted wind direction in degrees",
        ),
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=True,
            comment="Forecasted temperature in Celsius",
        ),
        sa.Column(
            "weather_model",
            sa.String(100),
            nullable=True,
            comment="Weather model used for forecast",
        ),
        sa.Column(
            "forecast_horizon_hours",
            sa.Integer(),
            nullable=True,
            comment="How many hours ahead this forecast is",
        ),
        sa.ForeignKeyConstraint(
            ["wind_farm_id"],
            ["windfarm.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_windgenerationforecast_forecast_time",
        "windgenerationforecast",
        ["forecast_time"],
        unique=False,
    )
    op.create_index(
        "ix_windgenerationforecast_wind_farm_id",
        "windgenerationforecast",
        ["wind_farm_id"],
        unique=False,
    )
    op.create_index(
        "ix_windgenerationforecast_created_at",
        "windgenerationforecast",
        ["created_at"],
        unique=False,
    )

    # Create forecastrun table
    op.create_table(
        "forecastrun",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wind_farm_id", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("records_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forecast_hours", sa.Integer(), nullable=False, server_default="48"),
        sa.Column("weather_model", sa.String(100), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["wind_farm_id"],
            ["windfarm.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("forecastrun")
    op.drop_index(
        "ix_windgenerationforecast_created_at", table_name="windgenerationforecast"
    )
    op.drop_index(
        "ix_windgenerationforecast_wind_farm_id", table_name="windgenerationforecast"
    )
    op.drop_index(
        "ix_windgenerationforecast_forecast_time", table_name="windgenerationforecast"
    )
    op.drop_table("windgenerationforecast")
