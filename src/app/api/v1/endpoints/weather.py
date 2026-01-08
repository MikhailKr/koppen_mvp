"""Weather data API endpoints."""

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser
from app.schemas.weather import (
    WeatherDataOut,
    WeatherModelsOut,
    WeatherRecordOut,
    WeatherResolutionsOut,
)
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/", response_model=WeatherDataOut)
async def get_weather_data(
    current_user: CurrentUser,
    latitude: float = Query(..., ge=-90, le=90, description="Location latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Location longitude"),
    model: str = Query("icon_global", description="Weather model to use"),
    past_days: int = Query(7, ge=1, le=90, description="Number of historical days"),
    forecast_days: int = Query(7, ge=1, le=16, description="Number of forecast days"),
    resolution_minutes: int = Query(
        60, description="Resolution in minutes (15, 30, 60)"
    ),
) -> WeatherDataOut:
    """Fetch weather data for a location.

    Returns historical and forecast weather data from Open-Meteo API.
    """
    service = WeatherService()
    response = await service.get_weather_data(
        latitude=latitude,
        longitude=longitude,
        model=model,
        past_days=past_days,
        forecast_days=forecast_days,
        resolution_minutes=resolution_minutes,
    )

    return WeatherDataOut(
        historical=[
            WeatherRecordOut(
                time=r.time,
                temperature=r.temperature,
                temperature_80m=r.temperature_80m,
                wind_speed=r.wind_speed,
                wind_speed_80m=r.wind_speed_80m,
                wind_speed_100m=r.wind_speed_100m,
                wind_direction=r.wind_direction,
                wind_direction_80m=r.wind_direction_80m,
                wind_direction_100m=r.wind_direction_100m,
                pressure=r.pressure,
                precipitation=r.precipitation,
                cloud_cover=r.cloud_cover,
            )
            for r in response.historical
        ],
        forecast=[
            WeatherRecordOut(
                time=r.time,
                temperature=r.temperature,
                temperature_80m=r.temperature_80m,
                wind_speed=r.wind_speed,
                wind_speed_80m=r.wind_speed_80m,
                wind_speed_100m=r.wind_speed_100m,
                wind_direction=r.wind_direction,
                wind_direction_80m=r.wind_direction_80m,
                wind_direction_100m=r.wind_direction_100m,
                pressure=r.pressure,
                precipitation=r.precipitation,
                cloud_cover=r.cloud_cover,
            )
            for r in response.forecast
        ],
        model_used=response.model_used,
        resolution_info=response.resolution_info,
        latitude=response.latitude,
        longitude=response.longitude,
    )


@router.get("/models", response_model=WeatherModelsOut)
async def get_weather_models(current_user: CurrentUser) -> WeatherModelsOut:
    """Get available weather models."""
    return WeatherModelsOut(models=WeatherService.get_available_models())


@router.get("/resolutions", response_model=WeatherResolutionsOut)
async def get_weather_resolutions(current_user: CurrentUser) -> WeatherResolutionsOut:
    """Get available data resolutions in minutes."""
    return WeatherResolutionsOut(resolutions=WeatherService.get_resolution_options())
