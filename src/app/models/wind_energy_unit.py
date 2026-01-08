"""Wind energy models for turbines, farms, and power curves."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.forecast import ForecastRun, WindGenerationForecast


class GranularityEnum(str, enum.Enum):
    """Time granularity for generation records."""

    min_1 = "1min"
    min_5 = "5min"
    min_15 = "15min"
    min_30 = "30min"
    min_60 = "60min"


class TurbineStatusEnum(str, enum.Enum):
    """Turbine operational status."""

    on = "on"
    off = "off"


if TYPE_CHECKING:
    from app.models.user import User


class Location(Base):
    """Geographic location for wind turbine fleets."""

    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    wind_turbine_fleets: Mapped[list["WindTurbineFleet"]] = relationship(
        "WindTurbineFleet", back_populates="location"
    )
    wind_records: Mapped[list["WindRecord"]] = relationship(
        "WindRecord", back_populates="location"
    )

    def __str__(self) -> str:
        return f"Location(id={self.id}, longitude={self.longitude}, latitude={self.latitude})"


class WindFarm(Base):
    """Wind farm containing multiple wind turbines."""

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wind_farms")
    wind_turbine_fleets: Mapped[list["WindTurbineFleet"]] = relationship(
        "WindTurbineFleet", back_populates="wind_farm", cascade="all, delete-orphan"
    )
    generation_records: Mapped[list["WindFarmGenerationRecord"]] = relationship(
        "WindFarmGenerationRecord",
        back_populates="wind_farm",
        cascade="all, delete-orphan",
    )
    generation_forecasts: Mapped[list["WindGenerationForecast"]] = relationship(
        "WindGenerationForecast",
        back_populates="wind_farm",
        cascade="all, delete-orphan",
    )
    forecast_runs: Mapped[list["ForecastRun"]] = relationship(
        "ForecastRun", back_populates="wind_farm", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return f"WindFarm(id={self.id}, name={self.name})"


class PowerCurve(Base):
    """Power curve mapping wind speed to power output."""

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wind_speed_value_map: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # Relationships
    wind_turbines: Mapped[list["WindTurbine"]] = relationship(
        "WindTurbine", back_populates="power_curve"
    )

    def add_entry(self, wind_speed: float, value: float) -> None:
        """Add a wind speed to power value mapping."""
        if self.wind_speed_value_map is None:
            self.wind_speed_value_map = {}
        self.wind_speed_value_map[str(wind_speed)] = value

    def __str__(self) -> str:
        return f"PowerCurve(id={self.id}, name={self.name})"


class WindTurbine(Base):
    """Wind turbine specification/template (reusable across projects)."""

    turbine_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hub_height: Mapped[float] = mapped_column(
        Float, nullable=False, default=100.0, doc="Height of the wind turbine in meters"
    )
    nominal_power: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        doc="Nominal power of the wind turbine in MW",
    )
    power_curve_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("powercurve.id"), nullable=True
    )

    # Relationships
    power_curve: Mapped["PowerCurve | None"] = relationship(
        "PowerCurve", back_populates="wind_turbines"
    )
    wind_turbine_fleets: Mapped[list["WindTurbineFleet"]] = relationship(
        "WindTurbineFleet", back_populates="wind_turbine"
    )
    generation_records: Mapped[list["WindTurbineGenerationRecord"]] = relationship(
        "WindTurbineGenerationRecord", back_populates="wind_turbine"
    )

    def __str__(self) -> str:
        return f"WindTurbine(id={self.id}, type={self.turbine_type}, power={self.nominal_power}MW)"


class WindTurbineFleet(Base):
    """Links turbine specs to a specific location within a wind farm."""

    wind_farm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("windfarm.id"), nullable=False
    )
    wind_turbine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("windturbine.id"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("location.id"), nullable=False
    )
    number_of_turbines: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    wind_farm: Mapped["WindFarm"] = relationship(
        "WindFarm", back_populates="wind_turbine_fleets"
    )
    wind_turbine: Mapped["WindTurbine"] = relationship(
        "WindTurbine", back_populates="wind_turbine_fleets"
    )
    location: Mapped["Location"] = relationship(
        "Location", back_populates="wind_turbine_fleets"
    )

    def __str__(self) -> str:
        return f"WindTurbineFleet(id={self.id}, count={self.number_of_turbines})"


class WindRecord(Base):
    """Historical wind measurement record."""

    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("location.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    wind_speed: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Wind speed in m/s"
    )
    wind_direction: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Wind direction in degrees"
    )
    temperature: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Temperature in Celsius"
    )

    # Relationships
    location: Mapped["Location"] = relationship(
        "Location", back_populates="wind_records"
    )

    def __str__(self) -> str:
        return f"WindRecord(id={self.id}, speed={self.wind_speed}m/s, dir={self.wind_direction}°)"


class WindTurbineGenerationRecord(Base):
    """Historical power generation record for a wind turbine.

    The wind_turbine_id is optional - if not provided, this represents
    an aggregated record without specific turbine information.
    """

    wind_turbine_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("windturbine.id"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generation: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Power generation in kW"
    )
    granularity: Mapped[GranularityEnum] = mapped_column(
        Enum(GranularityEnum), nullable=False, default=GranularityEnum.min_60
    )
    is_synthetic: Mapped[bool] = mapped_column(
        nullable=False, default=False, doc="True if data is synthetically generated"
    )

    # Relationships
    wind_turbine: Mapped["WindTurbine | None"] = relationship(
        "WindTurbine", back_populates="generation_records"
    )

    def __str__(self) -> str:
        return f"GenerationRecord(id={self.id}, generation={self.generation}kW, synthetic={self.is_synthetic})"


class WindFarmGenerationRecord(Base):
    """Historical power generation record for an entire wind farm.

    Stores aggregated generation and individual turbine fleet statuses.
    """

    wind_farm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("windfarm.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generation: Mapped[float] = mapped_column(
        Float, nullable=False, doc="Total power generation in kW"
    )
    granularity: Mapped[GranularityEnum] = mapped_column(
        Enum(GranularityEnum), nullable=False, default=GranularityEnum.min_60
    )
    # Turbine fleet statuses: {fleet_id: "on" | "off"}
    fleet_statuses: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Status of each turbine fleet: {fleet_id: 'on'|'off'}",
    )
    is_synthetic: Mapped[bool] = mapped_column(
        nullable=False, default=False, doc="True if data is synthetically generated"
    )
    # Weather data used for generation
    wind_speed: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Average wind speed in m/s used for generation"
    )
    wind_direction: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Wind direction in degrees"
    )
    temperature: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Temperature in Celsius"
    )

    # Relationships
    wind_farm: Mapped["WindFarm"] = relationship(
        "WindFarm", back_populates="generation_records"
    )

    def __str__(self) -> str:
        return f"WindFarmGenerationRecord(id={self.id}, farm_id={self.wind_farm_id}, generation={self.generation}kW)"

    def set_fleet_status(self, fleet_id: int, status: TurbineStatusEnum) -> None:
        """Set the status of a turbine fleet."""
        if self.fleet_statuses is None:
            self.fleet_statuses = {}
        self.fleet_statuses[str(fleet_id)] = status.value

    def get_fleet_status(self, fleet_id: int) -> TurbineStatusEnum | None:
        """Get the status of a turbine fleet."""
        if self.fleet_statuses is None:
            return None
        status = self.fleet_statuses.get(str(fleet_id))
        return TurbineStatusEnum(status) if status else None

    def get_active_fleet_ids(self) -> list[int]:
        """Get list of fleet IDs that are active (on)."""
        if self.fleet_statuses is None:
            return []
        return [
            int(fleet_id)
            for fleet_id, status in self.fleet_statuses.items()
            if status == TurbineStatusEnum.on.value
        ]
