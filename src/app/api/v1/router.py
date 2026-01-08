"""API v1 router that aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    chat,
    forecasts,
    health,
    locations,
    records,
    synthetic,
    weather,
    wind_farms,
    wind_turbines,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(locations.router)
api_router.include_router(wind_farms.router)
api_router.include_router(wind_turbines.router)
api_router.include_router(records.router)
api_router.include_router(weather.router)
api_router.include_router(synthetic.router)
api_router.include_router(forecasts.router)
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
