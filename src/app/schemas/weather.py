"""Weather data schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class WeatherRecordOut(BaseModel):
    """Single weather data point output."""

    time: datetime
    temperature: float | None = None
    temperature_80m: float | None = None
    wind_speed: float | None = None
    wind_speed_80m: float | None = None
    wind_speed_100m: float | None = None
    wind_direction: float | None = None
    wind_direction_80m: float | None = None
    wind_direction_100m: float | None = None
    pressure: float | None = None
    precipitation: float | None = None
    cloud_cover: float | None = None


class WeatherDataOut(BaseModel):
    """Weather API response."""

    historical: list[WeatherRecordOut] = Field(default_factory=list)
    forecast: list[WeatherRecordOut] = Field(default_factory=list)
    model_used: str | None = None
    resolution_info: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class WeatherModelsOut(BaseModel):
    """Available weather models."""

    models: dict[str, str]


class WeatherResolutionsOut(BaseModel):
    """Available resolutions."""

    resolutions: list[int]
