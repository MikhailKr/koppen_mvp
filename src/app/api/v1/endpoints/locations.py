"""Location CRUD endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DatabaseSession
from app.models import Location
from app.schemas.wind_energy import LocationCreate, LocationRead, LocationUpdate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post("/", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_in: LocationCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Location:
    """Create a new location."""
    location = Location(
        longitude=location_in.longitude,
        latitude=location_in.latitude,
    )
    db.add(location)
    await db.flush()
    await db.refresh(location)
    return location


@router.get("/", response_model=list[LocationRead])
async def list_locations(
    db: DatabaseSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[Location]:
    """List all locations."""
    result = await db.execute(select(Location).offset(skip).limit(limit))
    return list(result.scalars().all())


@router.get("/{location_id}", response_model=LocationRead)
async def get_location(
    location_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Location:
    """Get a location by ID."""
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.patch("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: int,
    location_in: LocationUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Location:
    """Update a location."""
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = location_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    await db.flush()
    await db.refresh(location)
    return location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a location."""
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    await db.delete(location)

