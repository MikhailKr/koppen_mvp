"""Synthetic wind generation data service.

Uses historical weather data from Open-Meteo and windpowerlib
to generate synthetic power generation data for wind farms.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    GranularityEnum,
    Location,
    WindFarm,
    WindFarmGenerationRecord,
    WindTurbine,
    WindTurbineFleet,
)
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


@dataclass
class SyntheticGenerationConfig:
    """Configuration for synthetic data generation."""

    # Randomness settings
    add_noise: bool = False
    noise_std_percent: float = 5.0  # Standard deviation as % of power output
    random_outages: bool = False
    outage_probability: float = 0.01  # 1% chance per hour
    outage_duration_hours: int = 4  # Average outage duration


@dataclass
class SyntheticGenerationResult:
    """Result of synthetic generation."""

    wind_farm_id: int
    records_created: int
    start_time: datetime
    end_time: datetime
    total_generation_kwh: float
    config_used: SyntheticGenerationConfig | None = None


class SyntheticGenerationService:
    """Service for generating synthetic wind power data."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db: Database session.
        """
        self.db = db
        self.weather_service = WeatherService()

    async def generate_for_wind_farm(
        self,
        wind_farm_id: int,
        days_back: int = 30,
        granularity: GranularityEnum = GranularityEnum.min_60,
        config: SyntheticGenerationConfig | None = None,
    ) -> SyntheticGenerationResult:
        """Generate synthetic data for a wind farm.

        Args:
            wind_farm_id: ID of the wind farm.
            days_back: Number of days of historical data to generate.
            granularity: Time granularity for the records.
            config: Configuration for randomness and noise.

        Returns:
            SyntheticGenerationResult with generation statistics.
        """
        if config is None:
            config = SyntheticGenerationConfig()

        # Load wind farm with fleets and turbines
        wind_farm = await self._load_wind_farm(wind_farm_id)
        if not wind_farm:
            raise ValueError(f"Wind farm {wind_farm_id} not found")

        if not wind_farm.wind_turbine_fleets:
            raise ValueError(f"Wind farm {wind_farm_id} has no turbine fleets")

        # Get unique locations from fleets
        locations = await self._get_fleet_locations(wind_farm.wind_turbine_fleets)
        if not locations:
            raise ValueError(f"No locations found for wind farm {wind_farm_id}")

        # Convert granularity to minutes for weather API
        granularity_to_minutes = {
            GranularityEnum.min_1: 15,  # Open-Meteo minimum is 15 min
            GranularityEnum.min_5: 15,  # Open-Meteo minimum is 15 min
            GranularityEnum.min_15: 15,
            GranularityEnum.min_30: 60,  # Use hourly for 30min
            GranularityEnum.min_60: 60,
        }
        resolution_minutes = granularity_to_minutes.get(granularity, 60)

        # Fetch weather data for each location
        weather_data = await self._fetch_weather_for_locations(
            locations, days_back, resolution_minutes
        )

        # Calculate power output for each fleet
        generation_records = await self._calculate_generation(
            wind_farm=wind_farm,
            weather_data=weather_data,
            granularity=granularity,
            config=config,
        )

        # Get time range for deletion
        if generation_records:
            timestamps = [r.timestamp for r in generation_records]
            start_time = min(timestamps)
            end_time = max(timestamps)

            # Delete existing synthetic records for this wind farm in the same time range
            await self._delete_existing_synthetic_records(
                wind_farm_id=wind_farm_id,
                start_time=start_time,
                end_time=end_time,
            )

        # Save records to database
        records_created = await self._save_records(generation_records)

        # Calculate totals
        total_generation = sum(r.generation for r in generation_records)
        timestamps = [r.timestamp for r in generation_records]

        return SyntheticGenerationResult(
            wind_farm_id=wind_farm_id,
            records_created=records_created,
            start_time=min(timestamps) if timestamps else datetime.now(),
            end_time=max(timestamps) if timestamps else datetime.now(),
            total_generation_kwh=total_generation,
            config_used=config,
        )

    async def _load_wind_farm(self, wind_farm_id: int) -> WindFarm | None:
        """Load wind farm with all relationships."""
        result = await self.db.execute(
            select(WindFarm)
            .options(
                selectinload(WindFarm.wind_turbine_fleets)
                .selectinload(WindTurbineFleet.wind_turbine)
                .selectinload(WindTurbine.power_curve),
                selectinload(WindFarm.wind_turbine_fleets).selectinload(
                    WindTurbineFleet.location
                ),
            )
            .where(WindFarm.id == wind_farm_id)
        )
        return result.scalar_one_or_none()

    async def _get_fleet_locations(
        self, fleets: list[WindTurbineFleet]
    ) -> dict[int, Location]:
        """Get unique locations from fleets."""
        locations = {}
        for fleet in fleets:
            if fleet.location and fleet.location_id not in locations:
                locations[fleet.location_id] = fleet.location
        return locations

    async def _fetch_weather_for_locations(
        self,
        locations: dict[int, Location],
        days_back: int,
        resolution_minutes: int = 60,
    ) -> dict[int, pd.DataFrame]:
        """Fetch historical weather data for all locations."""
        weather_data = {}

        for loc_id, location in locations.items():
            logger.info(
                f"Fetching weather for location {loc_id}: ({location.latitude}, {location.longitude}) "
                f"at {resolution_minutes}min resolution"
            )

            response = await self.weather_service.get_weather_data(
                latitude=location.latitude,
                longitude=location.longitude,
                past_days=days_back,
                forecast_days=0,
                resolution_minutes=resolution_minutes,
            )

            if response.historical:
                # Convert to DataFrame
                df = pd.DataFrame(
                    [
                        {
                            "time": r.time,
                            "wind_speed": r.wind_speed,
                            "wind_speed_100m": r.wind_speed_100m,
                            "wind_direction": r.wind_direction,
                            "temperature": r.temperature,
                            "pressure": r.pressure,
                        }
                        for r in response.historical
                    ]
                )
                df["time"] = pd.to_datetime(df["time"])
                weather_data[loc_id] = df
                logger.info(f"Got {len(df)} weather records for location {loc_id}")
            else:
                logger.warning(f"No weather data for location {loc_id}")

        return weather_data

    async def _calculate_generation(
        self,
        wind_farm: WindFarm,
        weather_data: dict[int, pd.DataFrame],
        granularity: GranularityEnum,
        config: SyntheticGenerationConfig,
    ) -> list[WindFarmGenerationRecord]:
        """Calculate power generation for each timestamp."""
        records = []

        # Get all unique timestamps from weather data
        all_times = set()
        for df in weather_data.values():
            all_times.update(df["time"].tolist())

        all_times = sorted(all_times)

        # Track outages for each fleet
        fleet_outage_remaining: dict[int, int] = {}

        for timestamp in all_times:
            total_generation = 0.0
            fleet_statuses = {}
            # Track weather data (average across all fleets for this timestamp)
            wind_speeds: list[float] = []
            wind_directions: list[float] = []
            temperatures: list[float] = []

            for fleet in wind_farm.wind_turbine_fleets:
                # Check for random outages
                if config.random_outages:
                    # Decrement outage counter
                    if (
                        fleet.id in fleet_outage_remaining
                        and fleet_outage_remaining[fleet.id] > 0
                    ):
                        fleet_outage_remaining[fleet.id] -= 1
                        fleet_statuses[str(fleet.id)] = "off"
                        continue
                    # Random chance of new outage
                    if np.random.random() < config.outage_probability:
                        fleet_outage_remaining[fleet.id] = config.outage_duration_hours
                        fleet_statuses[str(fleet.id)] = "off"
                        continue

                # Get weather for this fleet's location
                if fleet.location_id not in weather_data:
                    fleet_statuses[str(fleet.id)] = "off"
                    continue

                weather_df = weather_data[fleet.location_id]
                weather_row = weather_df[weather_df["time"] == timestamp]

                if weather_row.empty:
                    fleet_statuses[str(fleet.id)] = "off"
                    continue

                # Get wind speed at hub height (use 100m or 10m)
                wind_speed = weather_row["wind_speed_100m"].iloc[0]
                if pd.isna(wind_speed):
                    wind_speed = weather_row["wind_speed"].iloc[0]

                if pd.isna(wind_speed):
                    fleet_statuses[str(fleet.id)] = "off"
                    continue

                # Collect weather data
                wind_speeds.append(float(wind_speed))
                wind_dir = weather_row["wind_direction"].iloc[0]
                if not pd.isna(wind_dir):
                    wind_directions.append(float(wind_dir))
                temp = weather_row["temperature"].iloc[0]
                if not pd.isna(temp):
                    temperatures.append(float(temp))

                # Calculate power output
                turbine = fleet.wind_turbine
                if turbine:
                    power_kw = self._calculate_turbine_power(
                        wind_speed=wind_speed,
                        turbine=turbine,
                        num_turbines=fleet.number_of_turbines,
                    )

                    # Add noise if configured
                    if config.add_noise and power_kw > 0:
                        noise_std = power_kw * (config.noise_std_percent / 100.0)
                        noise = np.random.normal(0, noise_std)
                        power_kw = max(0, power_kw + noise)  # Ensure non-negative

                    total_generation += power_kw
                    fleet_statuses[str(fleet.id)] = "on" if power_kw > 0 else "off"
                else:
                    fleet_statuses[str(fleet.id)] = "off"

            # Create record - convert pandas Timestamp to timezone-aware datetime
            if isinstance(timestamp, pd.Timestamp):
                ts = timestamp.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
            else:
                ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)

            # Calculate average weather values
            avg_wind_speed = (
                sum(wind_speeds) / len(wind_speeds) if wind_speeds else None
            )
            avg_wind_dir = (
                sum(wind_directions) / len(wind_directions) if wind_directions else None
            )
            avg_temp = sum(temperatures) / len(temperatures) if temperatures else None

            record = WindFarmGenerationRecord(
                wind_farm_id=wind_farm.id,
                timestamp=ts,
                generation=round(total_generation, 2),
                granularity=granularity,
                fleet_statuses=fleet_statuses,
                is_synthetic=True,
                wind_speed=round(avg_wind_speed, 2) if avg_wind_speed else None,
                wind_direction=round(avg_wind_dir, 1) if avg_wind_dir else None,
                temperature=round(avg_temp, 1) if avg_temp else None,
            )
            records.append(record)

        return records

    def _calculate_turbine_power(
        self,
        wind_speed: float,
        turbine: WindTurbine,
        num_turbines: int = 1,
    ) -> float:
        """Calculate power output for a turbine at given wind speed.

        Uses power curve if available, otherwise uses simplified model.
        """
        if wind_speed <= 0:
            return 0.0

        # Use power curve if available
        if turbine.power_curve and turbine.power_curve.wind_speed_value_map:
            power_curve = turbine.power_curve.wind_speed_value_map
            power_kw = self._interpolate_power_curve(wind_speed, power_curve)
        else:
            # Simplified power calculation based on nominal power
            # Using typical wind turbine characteristics
            cut_in = 3.0  # m/s
            rated_speed = 12.0  # m/s
            cut_out = 25.0  # m/s
            nominal_power_kw = turbine.nominal_power * 1000  # MW to kW

            if wind_speed < cut_in:
                power_kw = 0.0
            elif wind_speed < rated_speed:
                # Cubic relationship in this region
                power_kw = (
                    nominal_power_kw
                    * ((wind_speed - cut_in) / (rated_speed - cut_in)) ** 3
                )
            elif wind_speed <= cut_out:
                power_kw = nominal_power_kw
            else:
                power_kw = 0.0  # Shutdown above cut-out

        return power_kw * num_turbines

    def _interpolate_power_curve(
        self,
        wind_speed: float,
        power_curve: dict[str, float],
    ) -> float:
        """Interpolate power from power curve."""
        # Convert keys to float and sort
        points = [(float(k), v) for k, v in power_curve.items()]
        points.sort(key=lambda x: x[0])

        if not points:
            return 0.0

        speeds = [p[0] for p in points]
        powers = [p[1] for p in points]

        # Use numpy interpolation
        return float(np.interp(wind_speed, speeds, powers))

    async def _delete_existing_synthetic_records(
        self,
        wind_farm_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Delete existing synthetic records for a wind farm in a time range.

        Args:
            wind_farm_id: ID of the wind farm.
            start_time: Start of the time range.
            end_time: End of the time range.

        Returns:
            Number of records deleted.
        """
        # Delete synthetic records in the time range
        stmt = delete(WindFarmGenerationRecord).where(
            WindFarmGenerationRecord.wind_farm_id == wind_farm_id,
            WindFarmGenerationRecord.is_synthetic == True,  # noqa: E712
            WindFarmGenerationRecord.timestamp >= start_time,
            WindFarmGenerationRecord.timestamp <= end_time,
        )
        result = await self.db.execute(stmt)
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} existing synthetic records for wind farm {wind_farm_id} "
                f"between {start_time} and {end_time}"
            )

        return deleted_count

    async def _save_records(
        self,
        records: list[WindFarmGenerationRecord],
    ) -> int:
        """Save generation records to database."""
        if not records:
            return 0

        self.db.add_all(records)
        await self.db.flush()

        logger.info(f"Saved {len(records)} synthetic generation records")
        return len(records)
