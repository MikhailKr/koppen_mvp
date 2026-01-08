"""Synthetic data generation endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DatabaseSession
from app.models import GranularityEnum
from app.services.synthetic_generation import (
    SyntheticGenerationConfig,
    SyntheticGenerationService,
)

router = APIRouter(prefix="/synthetic", tags=["synthetic"])


class SyntheticGenerationRequest(BaseModel):
    """Request schema for synthetic data generation."""

    wind_farm_id: int = Field(..., description="ID of the wind farm")
    days_back: int = Field(
        default=30, ge=1, le=365, description="Days of historical data"
    )
    granularity: GranularityEnum = Field(
        default=GranularityEnum.min_60,
        description="Time granularity for records",
    )
    # Randomness settings
    add_noise: bool = Field(
        default=False, description="Add Gaussian noise to power output"
    )
    noise_std_percent: float = Field(
        default=5.0,
        ge=0,
        le=50,
        description="Standard deviation of noise as % of power output",
    )
    random_outages: bool = Field(
        default=False, description="Simulate random turbine outages"
    )
    outage_probability: float = Field(
        default=0.01,
        ge=0,
        le=1,
        description="Probability of outage per hour (0-1)",
    )
    outage_duration_hours: int = Field(
        default=4,
        ge=1,
        le=168,
        description="Average outage duration in hours",
    )


class SyntheticGenerationResponse(BaseModel):
    """Response schema for synthetic data generation."""

    wind_farm_id: int
    records_created: int
    start_time: datetime
    end_time: datetime
    total_generation_kwh: float
    message: str
    noise_applied: bool
    outages_simulated: bool


@router.post(
    "/generate",
    response_model=SyntheticGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_synthetic_data(
    request: SyntheticGenerationRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> SyntheticGenerationResponse:
    """Generate synthetic wind generation data for a wind farm.

    This endpoint:
    1. Fetches historical weather data from Open-Meteo
    2. Uses wind turbine specs and power curves from the database
    3. Calculates synthetic power generation using windpowerlib-like calculations
    4. Optionally adds Gaussian noise and random outages
    5. Saves records to the database with is_synthetic=True
    """
    service = SyntheticGenerationService(db)

    # Build config from request
    config = SyntheticGenerationConfig(
        add_noise=request.add_noise,
        noise_std_percent=request.noise_std_percent,
        random_outages=request.random_outages,
        outage_probability=request.outage_probability,
        outage_duration_hours=request.outage_duration_hours,
    )

    try:
        result = await service.generate_for_wind_farm(
            wind_farm_id=request.wind_farm_id,
            days_back=request.days_back,
            granularity=request.granularity,
            config=config,
        )

        return SyntheticGenerationResponse(
            wind_farm_id=result.wind_farm_id,
            records_created=result.records_created,
            start_time=result.start_time,
            end_time=result.end_time,
            total_generation_kwh=result.total_generation_kwh,
            message=f"Successfully generated {result.records_created} synthetic records",
            noise_applied=request.add_noise,
            outages_simulated=request.random_outages,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate synthetic data: {str(e)}",
        ) from e
