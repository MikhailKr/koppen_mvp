"""Forecast models for wind power predictions."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.wind_energy_unit import GranularityEnum

if TYPE_CHECKING:
    from app.models.wind_energy_unit import WindFarm


class ForecastModelEnum(str, enum.Enum):
    """Weather model used for forecast."""

    openmeteo_best_match = "best_match"
    openmeteo_gfs = "gfs_seamless"
    openmeteo_ecmwf = "ecmwf_ifs025"
    openmeteo_icon = "icon_seamless"


class WindGenerationForecast(Base):
    """Forecasted power generation for a wind farm.

    Similar to WindFarmGenerationRecord but for future predictions.
    """

    wind_farm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("windfarm.id"), nullable=False
    )
    # When the forecast was generated
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # The future timestamp this forecast is for
    forecast_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Forecasted generation
    generation: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Forecasted power generation in kW"
    )
    granularity: Mapped[GranularityEnum] = mapped_column(
        Enum(GranularityEnum), nullable=False, default=GranularityEnum.min_60
    )
    # Weather data used for forecast
    wind_speed: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Forecasted wind speed in m/s"
    )
    wind_direction: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Forecasted wind direction in degrees"
    )
    temperature: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Forecasted temperature in Celsius"
    )
    # Metadata
    weather_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Weather model used for forecast"
    )
    forecast_horizon_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="How many hours ahead this forecast is"
    )

    # Relationships
    wind_farm: Mapped["WindFarm"] = relationship(
        "WindFarm", back_populates="generation_forecasts"
    )

    def __str__(self) -> str:
        return (
            f"WindGenerationForecast(id={self.id}, farm_id={self.wind_farm_id}, "
            f"forecast_time={self.forecast_time}, generation={self.generation}kW)"
        )


class ForecastRun(Base):
    """Record of a forecast pipeline run."""

    wind_farm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("windfarm.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running"
    )  # running, success, failed
    records_created: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    forecast_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=48
    )
    weather_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )

    # Relationships
    wind_farm: Mapped["WindFarm"] = relationship("WindFarm", back_populates="forecast_runs")

    def __str__(self) -> str:
        return f"ForecastRun(id={self.id}, status={self.status})"
