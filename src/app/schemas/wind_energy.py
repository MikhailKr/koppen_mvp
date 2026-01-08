"""Schemas for wind energy models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.wind_energy_unit import GranularityEnum


# ============== Location Schemas ==============
class LocationBase(BaseModel):
    """Base location schema."""

    longitude: float
    latitude: float


class LocationCreate(LocationBase):
    """Schema for creating a location."""

    pass


class LocationUpdate(BaseModel):
    """Schema for updating a location."""

    longitude: float | None = None
    latitude: float | None = None


class LocationRead(LocationBase):
    """Schema for reading a location."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ============== PowerCurve Schemas ==============
class PowerCurveBase(BaseModel):
    """Base power curve schema."""

    name: str | None = None
    wind_speed_value_map: dict[str, float] = {}


class PowerCurveCreate(PowerCurveBase):
    """Schema for creating a power curve."""

    pass


class PowerCurveUpdate(BaseModel):
    """Schema for updating a power curve."""

    name: str | None = None
    wind_speed_value_map: dict[str, float] | None = None


class PowerCurveRead(PowerCurveBase):
    """Schema for reading a power curve."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# ============== WindTurbine Schemas ==============
class WindTurbineBase(BaseModel):
    """Base wind turbine schema (reusable specification)."""

    turbine_type: str | None = None
    hub_height: float = 100.0
    nominal_power: float = 1.0
    power_curve_id: int | None = None


class WindTurbineCreate(WindTurbineBase):
    """Schema for creating a wind turbine specification."""

    pass


class WindTurbineUpdate(BaseModel):
    """Schema for updating a wind turbine specification."""

    turbine_type: str | None = None
    hub_height: float | None = None
    nominal_power: float | None = None
    power_curve_id: int | None = None


class WindTurbineRead(WindTurbineBase):
    """Schema for reading a wind turbine specification."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    power_curve: PowerCurveRead | None = None


# ============== WindFarm Schemas ==============
class WindFarmBase(BaseModel):
    """Base wind farm schema."""

    name: str
    description: str | None = None


class WindFarmCreate(WindFarmBase):
    """Schema for creating a wind farm."""

    pass


class WindFarmUpdate(BaseModel):
    """Schema for updating a wind farm."""

    name: str | None = None
    description: str | None = None


class WindFarmRead(WindFarmBase):
    """Schema for reading a wind farm."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


# ============== WindTurbineFleet Schemas ==============
class WindTurbineFleetBase(BaseModel):
    """Base wind turbine fleet schema (links turbine spec to location in a farm)."""

    wind_farm_id: int
    wind_turbine_id: int
    location_id: int
    number_of_turbines: int = 1


class WindTurbineFleetCreate(WindTurbineFleetBase):
    """Schema for creating a wind turbine fleet."""

    pass


class WindTurbineFleetUpdate(BaseModel):
    """Schema for updating a wind turbine fleet."""

    number_of_turbines: int | None = None
    location_id: int | None = None


class WindTurbineFleetRead(WindTurbineFleetBase):
    """Schema for reading a wind turbine fleet."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    location: LocationRead | None = None
    wind_turbine: WindTurbineRead | None = None


# ============== WindRecord Schemas ==============
class WindRecordBase(BaseModel):
    """Base wind record schema."""

    location_id: int
    timestamp: datetime
    wind_speed: float
    wind_direction: float
    temperature: float | None = None


class WindRecordCreate(WindRecordBase):
    """Schema for creating a wind record."""

    pass


class WindRecordBulkCreate(BaseModel):
    """Schema for bulk creating wind records."""

    records: list[WindRecordCreate]


class WindRecordRead(WindRecordBase):
    """Schema for reading a wind record."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# ============== WindTurbineGenerationRecord Schemas ==============
class GenerationRecordBase(BaseModel):
    """Base generation record schema.

    wind_turbine_id is optional - if not provided, represents aggregated data.
    """

    wind_turbine_id: int | None = None
    timestamp: datetime
    generation: float
    granularity: GranularityEnum = GranularityEnum.min_60
    is_synthetic: bool = False


class GenerationRecordCreate(GenerationRecordBase):
    """Schema for creating a generation record."""

    pass


class GenerationRecordBulkCreate(BaseModel):
    """Schema for bulk creating generation records."""

    records: list[GenerationRecordCreate]


class GenerationRecordRead(GenerationRecordBase):
    """Schema for reading a generation record."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# ============== WindFarmGenerationRecord Schemas ==============
class WindFarmGenerationRecordBase(BaseModel):
    """Base wind farm generation record schema."""

    wind_farm_id: int
    timestamp: datetime
    generation: float
    granularity: GranularityEnum = GranularityEnum.min_60
    fleet_statuses: dict[str, str] = {}  # {fleet_id: "on"|"off"}
    is_synthetic: bool = False
    # Weather data used for generation
    wind_speed: float | None = None
    wind_direction: float | None = None
    temperature: float | None = None


class WindFarmGenerationRecordCreate(WindFarmGenerationRecordBase):
    """Schema for creating a wind farm generation record."""

    pass


class WindFarmGenerationRecordBulkCreate(BaseModel):
    """Schema for bulk creating wind farm generation records."""

    records: list[WindFarmGenerationRecordCreate]


class WindFarmGenerationRecordRead(WindFarmGenerationRecordBase):
    """Schema for reading a wind farm generation record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
