"""WindFarm CRUD endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DatabaseSession
from app.models import WindFarm
from app.schemas.wind_energy import WindFarmCreate, WindFarmRead, WindFarmUpdate

router = APIRouter(prefix="/wind-farms", tags=["wind-farms"])


@router.post("/", response_model=WindFarmRead, status_code=status.HTTP_201_CREATED)
async def create_wind_farm(
    wind_farm_in: WindFarmCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindFarm:
    """Create a new wind farm for the current user."""
    wind_farm = WindFarm(
        name=wind_farm_in.name,
        description=wind_farm_in.description,
        user_id=current_user.id,
    )
    db.add(wind_farm)
    await db.flush()
    await db.refresh(wind_farm)
    return wind_farm


@router.get("/", response_model=list[WindFarmRead])
async def list_wind_farms(
    db: DatabaseSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[WindFarm]:
    """List all wind farms for the current user."""
    result = await db.execute(
        select(WindFarm)
        .where(WindFarm.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{wind_farm_id}", response_model=WindFarmRead)
async def get_wind_farm(
    wind_farm_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindFarm:
    """Get a wind farm by ID."""
    result = await db.execute(
        select(WindFarm).where(
            WindFarm.id == wind_farm_id,
            WindFarm.user_id == current_user.id,
        )
    )
    wind_farm = result.scalar_one_or_none()
    if not wind_farm:
        raise HTTPException(status_code=404, detail="Wind farm not found")
    return wind_farm


@router.patch("/{wind_farm_id}", response_model=WindFarmRead)
async def update_wind_farm(
    wind_farm_id: int,
    wind_farm_in: WindFarmUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindFarm:
    """Update a wind farm."""
    result = await db.execute(
        select(WindFarm).where(
            WindFarm.id == wind_farm_id,
            WindFarm.user_id == current_user.id,
        )
    )
    wind_farm = result.scalar_one_or_none()
    if not wind_farm:
        raise HTTPException(status_code=404, detail="Wind farm not found")

    update_data = wind_farm_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(wind_farm, field, value)

    await db.flush()
    await db.refresh(wind_farm)
    return wind_farm


@router.delete("/{wind_farm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wind_farm(
    wind_farm_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a wind farm."""
    result = await db.execute(
        select(WindFarm).where(
            WindFarm.id == wind_farm_id,
            WindFarm.user_id == current_user.id,
        )
    )
    wind_farm = result.scalar_one_or_none()
    if not wind_farm:
        raise HTTPException(status_code=404, detail="Wind farm not found")

    await db.delete(wind_farm)

