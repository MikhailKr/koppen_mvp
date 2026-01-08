"""WindTurbine, PowerCurve, and Fleet CRUD endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DatabaseSession
from app.models import PowerCurve, WindTurbine, WindTurbineFleet
from app.schemas.wind_energy import (
    PowerCurveCreate,
    PowerCurveRead,
    PowerCurveUpdate,
    WindTurbineCreate,
    WindTurbineFleetCreate,
    WindTurbineFleetRead,
    WindTurbineFleetUpdate,
    WindTurbineRead,
    WindTurbineUpdate,
)
from app.services.turbine_library_service import import_wind_turbine_library

router = APIRouter(tags=["wind-turbines"])


# ============== Windpowerlib Library Import Endpoint ==============
@router.post(
    "/import-turbine-library",
    tags=["turbine-library"],
    summary="Import all turbines from windpowerlib OEDB",
)
async def import_wind_turbines(
    db: DatabaseSession,
    current_user: CurrentUser,
) -> dict:
    """Import all wind turbines and power curves from windpowerlib's Open Energy Database.

    Skips turbines that already exist (by turbine_type). Does not delete existing data.
    """
    skipped_count = 0

    # Get existing turbine types to skip duplicates
    result = await db.execute(select(WindTurbine.turbine_type))
    existing_types = {t for t in result.scalars().all() if t}

    wind_turbines_data = import_wind_turbine_library()
    imported: list[WindTurbine] = []

    for power_curve_data, wind_turbine_data in wind_turbines_data:
        turbine_type = wind_turbine_data.get("turbine_type")

        # Skip if already exists
        if turbine_type in existing_types:
            skipped_count += 1
            continue

        # Create and store PowerCurve
        new_power_curve = PowerCurve(wind_speed_value_map=power_curve_data)
        db.add(new_power_curve)
        await db.flush()
        await db.refresh(new_power_curve)

        # Attach the new power_curve_id to wind turbine
        wind_turbine_data["power_curve_id"] = new_power_curve.id

        new_wind_turbine = WindTurbine(**wind_turbine_data)
        db.add(new_wind_turbine)
        await db.flush()

        imported.append(new_wind_turbine)
        existing_types.add(turbine_type)  # Track to avoid duplicates in same batch

    return {
        "message": f"Imported {len(imported)} turbines, skipped {skipped_count} duplicates",
        "imported": len(imported),
        "skipped": skipped_count,
    }


# ============== PowerCurve Endpoints ==============
@router.post(
    "/power-curves/",
    response_model=PowerCurveRead,
    status_code=status.HTTP_201_CREATED,
    tags=["power-curves"],
)
async def create_power_curve(
    power_curve_in: PowerCurveCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> PowerCurve:
    """Create a new power curve."""
    power_curve = PowerCurve(
        name=power_curve_in.name,
        wind_speed_value_map=power_curve_in.wind_speed_value_map,
    )
    db.add(power_curve)
    await db.flush()
    await db.refresh(power_curve)
    return power_curve


@router.get(
    "/power-curves/", response_model=list[PowerCurveRead], tags=["power-curves"]
)
async def list_power_curves(
    db: DatabaseSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[PowerCurve]:
    """List all power curves."""
    result = await db.execute(select(PowerCurve).offset(skip).limit(limit))
    return list(result.scalars().all())


@router.get(
    "/power-curves/{power_curve_id}",
    response_model=PowerCurveRead,
    tags=["power-curves"],
)
async def get_power_curve(
    power_curve_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> PowerCurve:
    """Get a power curve by ID."""
    result = await db.execute(select(PowerCurve).where(PowerCurve.id == power_curve_id))
    power_curve = result.scalar_one_or_none()
    if not power_curve:
        raise HTTPException(status_code=404, detail="Power curve not found")
    return power_curve


@router.patch(
    "/power-curves/{power_curve_id}",
    response_model=PowerCurveRead,
    tags=["power-curves"],
)
async def update_power_curve(
    power_curve_id: int,
    power_curve_in: PowerCurveUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> PowerCurve:
    """Update a power curve."""
    result = await db.execute(select(PowerCurve).where(PowerCurve.id == power_curve_id))
    power_curve = result.scalar_one_or_none()
    if not power_curve:
        raise HTTPException(status_code=404, detail="Power curve not found")

    update_data = power_curve_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(power_curve, field, value)

    await db.flush()
    await db.refresh(power_curve)
    return power_curve


@router.delete(
    "/power-curves/{power_curve_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["power-curves"],
)
async def delete_power_curve(
    power_curve_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a power curve."""
    result = await db.execute(select(PowerCurve).where(PowerCurve.id == power_curve_id))
    power_curve = result.scalar_one_or_none()
    if not power_curve:
        raise HTTPException(status_code=404, detail="Power curve not found")
    await db.delete(power_curve)


# ============== WindTurbine Endpoints ==============
@router.post(
    "/wind-turbines/",
    response_model=WindTurbineRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_wind_turbine(
    turbine_in: WindTurbineCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindTurbine:
    """Create a new wind turbine specification."""
    turbine = WindTurbine(
        turbine_type=turbine_in.turbine_type,
        hub_height=turbine_in.hub_height,
        nominal_power=turbine_in.nominal_power,
        power_curve_id=turbine_in.power_curve_id,
    )
    db.add(turbine)
    await db.flush()

    # Reload with relationships for response
    result = await db.execute(
        select(WindTurbine)
        .options(selectinload(WindTurbine.power_curve))
        .where(WindTurbine.id == turbine.id)
    )
    return result.scalar_one()


@router.get("/wind-turbines/", response_model=list[WindTurbineRead])
async def list_wind_turbines(
    db: DatabaseSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[WindTurbine]:
    """List all wind turbine specifications."""
    result = await db.execute(
        select(WindTurbine)
        .options(selectinload(WindTurbine.power_curve))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/wind-turbines/{turbine_id}", response_model=WindTurbineRead)
async def get_wind_turbine(
    turbine_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindTurbine:
    """Get a wind turbine specification by ID."""
    result = await db.execute(
        select(WindTurbine)
        .options(selectinload(WindTurbine.power_curve))
        .where(WindTurbine.id == turbine_id)
    )
    turbine = result.scalar_one_or_none()
    if not turbine:
        raise HTTPException(status_code=404, detail="Wind turbine not found")
    return turbine


@router.patch("/wind-turbines/{turbine_id}", response_model=WindTurbineRead)
async def update_wind_turbine(
    turbine_id: int,
    turbine_in: WindTurbineUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindTurbine:
    """Update a wind turbine."""
    result = await db.execute(select(WindTurbine).where(WindTurbine.id == turbine_id))
    turbine = result.scalar_one_or_none()
    if not turbine:
        raise HTTPException(status_code=404, detail="Wind turbine not found")

    update_data = turbine_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(turbine, field, value)

    await db.flush()
    await db.refresh(turbine)
    return turbine


@router.delete("/wind-turbines/{turbine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wind_turbine(
    turbine_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a wind turbine."""
    result = await db.execute(select(WindTurbine).where(WindTurbine.id == turbine_id))
    turbine = result.scalar_one_or_none()
    if not turbine:
        raise HTTPException(status_code=404, detail="Wind turbine not found")
    await db.delete(turbine)


# ============== WindTurbineFleet Endpoints ==============
@router.post(
    "/fleets/",
    response_model=WindTurbineFleetRead,
    status_code=status.HTTP_201_CREATED,
    tags=["fleets"],
)
async def create_fleet(
    fleet_in: WindTurbineFleetCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindTurbineFleet:
    """Create a new wind turbine fleet (link turbine spec to location in a farm)."""
    fleet = WindTurbineFleet(
        wind_farm_id=fleet_in.wind_farm_id,
        wind_turbine_id=fleet_in.wind_turbine_id,
        location_id=fleet_in.location_id,
        number_of_turbines=fleet_in.number_of_turbines,
    )
    db.add(fleet)
    await db.flush()

    # Reload with relationships for response
    result = await db.execute(
        select(WindTurbineFleet)
        .options(
            selectinload(WindTurbineFleet.location),
            selectinload(WindTurbineFleet.wind_turbine).selectinload(
                WindTurbine.power_curve
            ),
        )
        .where(WindTurbineFleet.id == fleet.id)
    )
    return result.scalar_one()


@router.get("/fleets/", response_model=list[WindTurbineFleetRead], tags=["fleets"])
async def list_fleets(
    db: DatabaseSession,
    current_user: CurrentUser,
    wind_farm_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[WindTurbineFleet]:
    """List all fleets, optionally filtered by wind farm."""
    query = select(WindTurbineFleet).options(
        selectinload(WindTurbineFleet.location),
        selectinload(WindTurbineFleet.wind_turbine).selectinload(
            WindTurbine.power_curve
        ),
    )
    if wind_farm_id:
        query = query.where(WindTurbineFleet.wind_farm_id == wind_farm_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


@router.patch(
    "/fleets/{fleet_id}", response_model=WindTurbineFleetRead, tags=["fleets"]
)
async def update_fleet(
    fleet_id: int,
    fleet_in: WindTurbineFleetUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindTurbineFleet:
    """Update a fleet."""
    result = await db.execute(
        select(WindTurbineFleet).where(WindTurbineFleet.id == fleet_id)
    )
    fleet = result.scalar_one_or_none()
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")

    if fleet_in.number_of_turbines is not None:
        fleet.number_of_turbines = fleet_in.number_of_turbines
    if fleet_in.location_id is not None:
        fleet.location_id = fleet_in.location_id

    await db.flush()
    await db.refresh(fleet)
    return fleet


@router.delete(
    "/fleets/{fleet_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["fleets"]
)
async def delete_fleet(
    fleet_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a fleet."""
    result = await db.execute(
        select(WindTurbineFleet).where(WindTurbineFleet.id == fleet_id)
    )
    fleet = result.scalar_one_or_none()
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")
    await db.delete(fleet)
