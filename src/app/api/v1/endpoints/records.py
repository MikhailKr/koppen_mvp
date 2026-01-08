"""Wind and generation record endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DatabaseSession
from app.models import WindFarmGenerationRecord, WindRecord, WindTurbineGenerationRecord
from app.schemas.wind_energy import (
    GenerationRecordBulkCreate,
    GenerationRecordCreate,
    GenerationRecordRead,
    WindFarmGenerationRecordBulkCreate,
    WindFarmGenerationRecordCreate,
    WindFarmGenerationRecordRead,
    WindRecordBulkCreate,
    WindRecordCreate,
    WindRecordRead,
)

router = APIRouter(tags=["records"])


# ============== WindRecord Endpoints ==============
@router.post(
    "/wind-records/",
    response_model=WindRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=["wind-records"],
)
async def create_wind_record(
    record_in: WindRecordCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindRecord:
    """Create a new wind record."""
    record = WindRecord(
        location_id=record_in.location_id,
        timestamp=record_in.timestamp,
        wind_speed=record_in.wind_speed,
        wind_direction=record_in.wind_direction,
        temperature=record_in.temperature,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.post(
    "/wind-records/bulk",
    response_model=list[WindRecordRead],
    status_code=status.HTTP_201_CREATED,
    tags=["wind-records"],
)
async def create_wind_records_bulk(
    bulk_in: WindRecordBulkCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[WindRecord]:
    """Create multiple wind records in bulk."""
    records = [
        WindRecord(
            location_id=r.location_id,
            timestamp=r.timestamp,
            wind_speed=r.wind_speed,
            wind_direction=r.wind_direction,
            temperature=r.temperature,
        )
        for r in bulk_in.records
    ]
    db.add_all(records)
    await db.flush()
    for record in records:
        await db.refresh(record)
    return records


@router.get("/wind-records/", response_model=list[WindRecordRead], tags=["wind-records"])
async def list_wind_records(
    db: DatabaseSession,
    current_user: CurrentUser,
    location_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=1000),
) -> list[WindRecord]:
    """List wind records with optional filters."""
    query = select(WindRecord)

    if location_id:
        query = query.where(WindRecord.location_id == location_id)
    if start_time:
        query = query.where(WindRecord.timestamp >= start_time)
    if end_time:
        query = query.where(WindRecord.timestamp <= end_time)

    query = query.order_by(WindRecord.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete("/wind-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["wind-records"])
async def delete_wind_record(
    record_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a wind record."""
    result = await db.execute(select(WindRecord).where(WindRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Wind record not found")
    await db.delete(record)


# ============== GenerationRecord Endpoints ==============
@router.post(
    "/generation-records/",
    response_model=GenerationRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=["generation-records"],
)
async def create_generation_record(
    record_in: GenerationRecordCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindTurbineGenerationRecord:
    """Create a new generation record.

    wind_turbine_id is optional - if not provided, represents aggregated data.
    is_synthetic indicates if the data was synthetically generated.
    """
    record = WindTurbineGenerationRecord(
        wind_turbine_id=record_in.wind_turbine_id,  # Can be None
        timestamp=record_in.timestamp,
        generation=record_in.generation,
        granularity=record_in.granularity,
        is_synthetic=record_in.is_synthetic,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.post(
    "/generation-records/bulk",
    response_model=list[GenerationRecordRead],
    status_code=status.HTTP_201_CREATED,
    tags=["generation-records"],
)
async def create_generation_records_bulk(
    bulk_in: GenerationRecordBulkCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[WindTurbineGenerationRecord]:
    """Create multiple generation records in bulk."""
    records = [
        WindTurbineGenerationRecord(
            wind_turbine_id=r.wind_turbine_id,
            timestamp=r.timestamp,
            generation=r.generation,
            granularity=r.granularity,
            is_synthetic=r.is_synthetic,
        )
        for r in bulk_in.records
    ]
    db.add_all(records)
    await db.flush()
    for record in records:
        await db.refresh(record)
    return records


@router.get("/generation-records/", response_model=list[GenerationRecordRead], tags=["generation-records"])
async def list_generation_records(
    db: DatabaseSession,
    current_user: CurrentUser,
    wind_turbine_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=1000),
) -> list[WindTurbineGenerationRecord]:
    """List generation records with optional filters."""
    query = select(WindTurbineGenerationRecord)

    if wind_turbine_id:
        query = query.where(WindTurbineGenerationRecord.wind_turbine_id == wind_turbine_id)
    if start_time:
        query = query.where(WindTurbineGenerationRecord.timestamp >= start_time)
    if end_time:
        query = query.where(WindTurbineGenerationRecord.timestamp <= end_time)

    query = query.order_by(WindTurbineGenerationRecord.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete(
    "/generation-records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["generation-records"],
)
async def delete_generation_record(
    record_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a generation record."""
    result = await db.execute(
        select(WindTurbineGenerationRecord).where(WindTurbineGenerationRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Generation record not found")
    await db.delete(record)


# ============== WindFarmGenerationRecord Endpoints ==============
@router.post(
    "/farm-generation-records/",
    response_model=WindFarmGenerationRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=["farm-generation-records"],
)
async def create_farm_generation_record(
    record_in: WindFarmGenerationRecordCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindFarmGenerationRecord:
    """Create a new wind farm generation record.

    The fleet_statuses field should be a dict mapping fleet_id (as string) to status ("on" or "off").
    Example: {"1": "on", "2": "off", "3": "on"}
    """
    record = WindFarmGenerationRecord(
        wind_farm_id=record_in.wind_farm_id,
        timestamp=record_in.timestamp,
        generation=record_in.generation,
        granularity=record_in.granularity,
        fleet_statuses=record_in.fleet_statuses,
        is_synthetic=record_in.is_synthetic,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.post(
    "/farm-generation-records/bulk",
    response_model=list[WindFarmGenerationRecordRead],
    status_code=status.HTTP_201_CREATED,
    tags=["farm-generation-records"],
)
async def create_farm_generation_records_bulk(
    bulk_in: WindFarmGenerationRecordBulkCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[WindFarmGenerationRecord]:
    """Create multiple wind farm generation records in bulk."""
    records = [
        WindFarmGenerationRecord(
            wind_farm_id=r.wind_farm_id,
            timestamp=r.timestamp,
            generation=r.generation,
            granularity=r.granularity,
            fleet_statuses=r.fleet_statuses,
            is_synthetic=r.is_synthetic,
        )
        for r in bulk_in.records
    ]
    db.add_all(records)
    await db.flush()
    for record in records:
        await db.refresh(record)
    return records


@router.get(
    "/farm-generation-records/",
    response_model=list[WindFarmGenerationRecordRead],
    tags=["farm-generation-records"],
)
async def list_farm_generation_records(
    db: DatabaseSession,
    current_user: CurrentUser,
    wind_farm_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    skip: int = 0,
    limit: int = Query(default=1000, le=10000),
) -> list[WindFarmGenerationRecord]:
    """List wind farm generation records with optional filters."""
    query = select(WindFarmGenerationRecord)

    if wind_farm_id:
        query = query.where(WindFarmGenerationRecord.wind_farm_id == wind_farm_id)
    if start_time:
        query = query.where(WindFarmGenerationRecord.timestamp >= start_time)
    if end_time:
        query = query.where(WindFarmGenerationRecord.timestamp <= end_time)

    query = query.order_by(WindFarmGenerationRecord.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/farm-generation-records/{record_id}",
    response_model=WindFarmGenerationRecordRead,
    tags=["farm-generation-records"],
)
async def get_farm_generation_record(
    record_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> WindFarmGenerationRecord:
    """Get a specific wind farm generation record."""
    result = await db.execute(
        select(WindFarmGenerationRecord).where(WindFarmGenerationRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Farm generation record not found")
    return record


@router.delete(
    "/farm-generation-records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["farm-generation-records"],
)
async def delete_farm_generation_record(
    record_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Delete a wind farm generation record."""
    result = await db.execute(
        select(WindFarmGenerationRecord).where(WindFarmGenerationRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Farm generation record not found")
    await db.delete(record)

