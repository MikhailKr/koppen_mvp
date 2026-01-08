"""Forecast API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models import ForecastRun, GranularityEnum, WindGenerationForecast
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


# ==================== Schemas ====================


class ForecastRequest(BaseModel):
    """Request to generate a forecast."""

    wind_farm_id: int
    forecast_hours: int = 48
    granularity: str = "60min"
    weather_model: str = "best_match"


class ForecastResponse(BaseModel):
    """Response after generating a forecast."""

    wind_farm_id: int
    run_id: int
    message: str
    records_created: int = 0
    forecast_start: datetime | None = None
    forecast_end: datetime | None = None
    weather_model: str | None = None
    total_forecasted_generation_kwh: float = 0.0


class ForecastRecordOut(BaseModel):
    """Forecast record output schema."""

    id: int
    wind_farm_id: int
    created_at: datetime
    forecast_time: datetime
    generation: float
    granularity: str
    wind_speed: float | None = None
    wind_direction: float | None = None
    temperature: float | None = None
    weather_model: str | None = None
    forecast_horizon_hours: int | None = None

    class Config:
        from_attributes = True


class ForecastRunOut(BaseModel):
    """Forecast run output schema."""

    id: int
    wind_farm_id: int
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    records_created: int
    forecast_hours: int
    weather_model: str | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True


# ==================== Endpoints ====================


@router.post(
    "/generate",
    response_model=ForecastResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_forecast(
    request: ForecastRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ForecastResponse:
    """Generate wind power forecast for a wind farm.

    Uses Open-Meteo weather forecast data and wind farm configuration
    to predict future power generation.
    """
    # Map granularity string to enum (supports both formats)
    granularity_map = {
        "1min": GranularityEnum.min_1,
        "5min": GranularityEnum.min_5,
        "15min": GranularityEnum.min_15,
        "30min": GranularityEnum.min_30,
        "60min": GranularityEnum.min_60,
        "min_1": GranularityEnum.min_1,
        "min_5": GranularityEnum.min_5,
        "min_15": GranularityEnum.min_15,
        "min_30": GranularityEnum.min_30,
        "min_60": GranularityEnum.min_60,
    }
    granularity = granularity_map.get(request.granularity, GranularityEnum.min_60)

    service = ForecastService(db)

    try:
        result = await service.generate_forecast(
            wind_farm_id=request.wind_farm_id,
            forecast_hours=request.forecast_hours,
            granularity=granularity,
            weather_model=request.weather_model,
        )

        await db.commit()

        return ForecastResponse(
            wind_farm_id=result.wind_farm_id,
            run_id=result.run_id,
            message="Forecast generated successfully",
            records_created=result.records_created,
            forecast_start=result.forecast_start,
            forecast_end=result.forecast_end,
            weather_model=result.weather_model,
            total_forecasted_generation_kwh=result.total_forecasted_generation_kwh,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate forecast: {e}",
        )


class HistoricalForecastRequest(BaseModel):
    """Request to generate historical forecast."""

    wind_farm_id: int
    days_back: int = 30
    granularity: str = "min_60"


@router.post(
    "/generate-historical",
    response_model=ForecastResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_historical_forecast(
    request: HistoricalForecastRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ForecastResponse:
    """Generate historical forecast using past weather data.

    This creates forecast records for past dates, allowing comparison
    with actual generation data for accuracy analysis.
    """
    # Map granularity string to enum
    granularity_map = {
        "1min": GranularityEnum.min_1,
        "5min": GranularityEnum.min_5,
        "15min": GranularityEnum.min_15,
        "30min": GranularityEnum.min_30,
        "60min": GranularityEnum.min_60,
        "min_1": GranularityEnum.min_1,
        "min_5": GranularityEnum.min_5,
        "min_15": GranularityEnum.min_15,
        "min_30": GranularityEnum.min_30,
        "min_60": GranularityEnum.min_60,
    }
    granularity = granularity_map.get(request.granularity, GranularityEnum.min_60)

    service = ForecastService(db)

    try:
        result = await service.generate_historical_forecast(
            wind_farm_id=request.wind_farm_id,
            days_back=request.days_back,
            granularity=granularity,
        )

        await db.commit()

        return ForecastResponse(
            wind_farm_id=result.wind_farm_id,
            run_id=result.run_id,
            message="Historical forecast generated successfully",
            records_created=result.records_created,
            forecast_start=result.forecast_start,
            forecast_end=result.forecast_end,
            weather_model=result.weather_model,
            total_forecasted_generation_kwh=result.total_forecasted_generation_kwh,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate historical forecast: {e}",
        )


@router.get(
    "/",
    response_model=list[ForecastRecordOut],
)
async def list_forecasts(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    wind_farm_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=1000, le=10000),
) -> list[WindGenerationForecast]:
    """List forecast records with optional filters."""
    query = select(WindGenerationForecast)

    if wind_farm_id:
        query = query.where(WindGenerationForecast.wind_farm_id == wind_farm_id)
    if start_time:
        query = query.where(WindGenerationForecast.forecast_time >= start_time)
    if end_time:
        query = query.where(WindGenerationForecast.forecast_time <= end_time)

    query = query.order_by(WindGenerationForecast.forecast_time).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/runs",
    response_model=list[ForecastRunOut],
)
async def list_forecast_runs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    wind_farm_id: int | None = None,
    limit: int = Query(default=50, le=500),
) -> list[ForecastRun]:
    """List forecast pipeline runs."""
    query = select(ForecastRun)

    if wind_farm_id:
        query = query.where(ForecastRun.wind_farm_id == wind_farm_id)

    query = query.order_by(ForecastRun.started_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/request/{wind_farm_id}",
    response_model=list[ForecastRecordOut],
)
async def request_forecast(
    wind_farm_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    horizon_hours: int = Query(
        default=48, ge=1, le=168, description="Forecast horizon in hours"
    ),
    start_hours_from_now: int = Query(
        default=0, ge=0, description="Start offset in hours from now"
    ),
    granularity: str = Query(
        default="60min", description="Time resolution: 15min, 30min, or 60min"
    ),
) -> list[ForecastRecordOut]:
    """Request forecast data for a wind farm.

    This endpoint ALWAYS generates a new forecast on each request (similar to /generate).
    Returns forecast data in the requested format with time horizon and granularity.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import and_, delete

    # Verify ownership
    from app.models import WindFarm

    farm_stmt = select(WindFarm).where(
        WindFarm.id == wind_farm_id, WindFarm.user_id == current_user.id
    )
    farm_result = await db.execute(farm_stmt)
    if not farm_result.scalar_one_or_none():
        raise HTTPException(
            status_code=404, detail="Wind farm not found or access denied"
        )

    # Map granularity string to enum
    granularity_map = {
        "15min": GranularityEnum.min_15,
        "30min": GranularityEnum.min_30,
        "60min": GranularityEnum.min_60,
    }
    gran_enum = granularity_map.get(granularity, GranularityEnum.min_60)

    # Always generate new forecast - delete old forecasts first
    await db.execute(
        delete(WindGenerationForecast).where(
            WindGenerationForecast.wind_farm_id == wind_farm_id
        )
    )

    # Generate new forecast
    service = ForecastService(db)
    try:
        await service.generate_forecast(
            wind_farm_id=wind_farm_id,
            forecast_hours=min(horizon_hours + start_hours_from_now, 168),
            granularity=gran_enum,
            weather_model="best_match",
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate forecast: {str(e)}"
        )

    # Calculate time range for filtering
    now = datetime.now(UTC)
    start_time = now + timedelta(hours=start_hours_from_now)
    end_time = start_time + timedelta(hours=horizon_hours)

    # Retrieve the newly generated forecasts matching the requested time range and granularity
    query = (
        select(WindGenerationForecast)
        .where(
            and_(
                WindGenerationForecast.wind_farm_id == wind_farm_id,
                WindGenerationForecast.forecast_time >= start_time,
                WindGenerationForecast.forecast_time <= end_time,
                WindGenerationForecast.granularity == gran_enum,
            )
        )
        .order_by(WindGenerationForecast.forecast_time.asc())
    )

    result = await db.execute(query)
    forecasts = list(result.scalars().all())

    return forecasts[:1000]  # Limit to 1000 records


@router.delete(
    "/{wind_farm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_forecasts(
    wind_farm_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all forecasts for a wind farm."""
    from sqlalchemy import delete

    await db.execute(
        delete(WindGenerationForecast).where(
            WindGenerationForecast.wind_farm_id == wind_farm_id
        )
    )
    await db.commit()
