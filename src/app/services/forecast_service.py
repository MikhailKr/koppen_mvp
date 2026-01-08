"""Wind generation forecast service.

Generates power generation forecasts using Open-Meteo weather forecasts
and wind farm configuration from the database.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ForecastRun,
    GranularityEnum,
    Location,
    WindFarm,
    WindGenerationForecast,
    WindTurbine,
    WindTurbineFleet,
)
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Result of a forecast generation run."""

    wind_farm_id: int
    run_id: int
    records_created: int
    forecast_start: datetime
    forecast_end: datetime
    weather_model: str | None
    total_forecasted_generation_kwh: float


class ForecastService:
    """Service for generating wind power forecasts."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the forecast service.

        Args:
            db: Database session.
        """
        self.db = db
        self.weather_service = WeatherService()

    async def generate_forecast(
        self,
        wind_farm_id: int,
        forecast_hours: int = 48,
        granularity: GranularityEnum = GranularityEnum.min_60,
        weather_model: str = "best_match",
    ) -> ForecastResult:
        """Generate power forecast for a wind farm.

        Args:
            wind_farm_id: ID of the wind farm.
            forecast_hours: Number of hours to forecast ahead.
            granularity: Time granularity for forecast points.
            weather_model: Open-Meteo weather model to use.

        Returns:
            ForecastResult with generation statistics.
        """
        # Create forecast run record
        run = ForecastRun(
            wind_farm_id=wind_farm_id,
            forecast_hours=forecast_hours,
            weather_model=weather_model,
            status="running",
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)

        try:
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

            # Convert granularity to minutes
            granularity_to_minutes = {
                GranularityEnum.min_1: 15,
                GranularityEnum.min_5: 15,
                GranularityEnum.min_15: 15,
                GranularityEnum.min_30: 60,
                GranularityEnum.min_60: 60,
            }
            resolution_minutes = granularity_to_minutes.get(granularity, 60)

            # Fetch forecast weather data for each location
            weather_data = await self._fetch_forecast_weather(
                locations=locations,
                forecast_days=max(1, forecast_hours // 24 + 1),
                resolution_minutes=resolution_minutes,
                weather_model=weather_model,
            )

            # Calculate power forecasts
            forecast_records = await self._calculate_forecasts(
                wind_farm=wind_farm,
                weather_data=weather_data,
                granularity=granularity,
                weather_model=weather_model,
                forecast_hours=forecast_hours,
            )

            # Delete old forecasts for this wind farm (keep only latest)
            if forecast_records:
                await self._delete_old_forecasts(wind_farm_id)

            # Save new forecasts
            records_created = await self._save_forecasts(forecast_records)

            # Update run status
            run.status = "success"
            run.records_created = records_created
            run.completed_at = datetime.now(timezone.utc)

            # Calculate totals
            total_generation = sum(r.generation for r in forecast_records)
            forecast_times = [r.forecast_time for r in forecast_records]

            return ForecastResult(
                wind_farm_id=wind_farm_id,
                run_id=run.id,
                records_created=records_created,
                forecast_start=min(forecast_times) if forecast_times else datetime.now(timezone.utc),
                forecast_end=max(forecast_times) if forecast_times else datetime.now(timezone.utc),
                weather_model=weather_model,
                total_forecasted_generation_kwh=total_generation,
            )

        except Exception as e:
            # Update run with error
            run.status = "failed"
            run.error_message = str(e)[:1000]
            run.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
            raise

    async def generate_historical_forecast(
        self,
        wind_farm_id: int,
        days_back: int = 30,
        granularity: GranularityEnum = GranularityEnum.min_60,
    ) -> ForecastResult:
        """Generate historical forecast using past weather data.

        This creates forecast records for past dates using historical weather,
        allowing comparison with actual generation data for accuracy analysis.

        Args:
            wind_farm_id: ID of the wind farm.
            days_back: Number of days back to generate forecasts for.
            granularity: Time granularity for forecast points.

        Returns:
            ForecastResult with generation statistics.
        """
        from datetime import timedelta

        # Create forecast run record
        run = ForecastRun(
            wind_farm_id=wind_farm_id,
            forecast_hours=days_back * 24,
            weather_model="historical",
            status="running",
        )
        self.db.add(run)
        await self.db.flush()

        try:
            # Load wind farm with relationships
            wind_farm = await self._load_wind_farm(wind_farm_id)
            if not wind_farm:
                raise ValueError(f"Wind farm {wind_farm_id} not found")

            if not wind_farm.wind_turbine_fleets:
                raise ValueError(f"Wind farm {wind_farm_id} has no turbine fleets")

            # Get locations
            locations = await self._get_fleet_locations(wind_farm.wind_turbine_fleets)
            if not locations:
                raise ValueError(f"No locations found for wind farm {wind_farm_id}")

            # Determine resolution
            granularity_to_minutes = {
                GranularityEnum.min_1: 15,
                GranularityEnum.min_5: 15,
                GranularityEnum.min_15: 15,
                GranularityEnum.min_30: 60,
                GranularityEnum.min_60: 60,
            }
            resolution_minutes = granularity_to_minutes.get(granularity, 60)

            # Fetch HISTORICAL weather data (not forecast)
            weather_data = await self._fetch_historical_weather(
                locations=locations,
                days_back=days_back,
                resolution_minutes=resolution_minutes,
            )

            # Calculate power forecasts using historical weather
            forecast_records = await self._calculate_historical_forecasts(
                wind_farm=wind_farm,
                weather_data=weather_data,
                granularity=granularity,
            )

            # Delete existing forecasts for same time range
            if forecast_records:
                start_time = min(r.forecast_time for r in forecast_records)
                end_time = max(r.forecast_time for r in forecast_records)
                await self._delete_forecasts_in_range(
                    wind_farm_id=wind_farm_id,
                    start_time=start_time,
                    end_time=end_time,
                )

            # Save records
            records_created = 0
            total_generation = 0.0
            for record in forecast_records:
                self.db.add(record)
                records_created += 1
                total_generation += record.generation

            await self.db.flush()

            # Update run status
            run.status = "completed"
            run.records_created = records_created
            run.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

            forecast_times = [r.forecast_time for r in forecast_records]

            return ForecastResult(
                wind_farm_id=wind_farm_id,
                run_id=run.id,
                records_created=records_created,
                forecast_start=min(forecast_times) if forecast_times else datetime.now(timezone.utc),
                forecast_end=max(forecast_times) if forecast_times else datetime.now(timezone.utc),
                weather_model="historical",
                total_forecasted_generation_kwh=total_generation,
            )

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)[:1000]
            run.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
            raise

    async def _fetch_historical_weather(
        self,
        locations: dict[int, Location],
        days_back: int,
        resolution_minutes: int,
    ) -> dict[int, pd.DataFrame]:
        """Fetch historical weather data for all locations."""
        weather_data = {}

        for loc_id, location in locations.items():
            logger.info(
                f"Fetching historical weather for location {loc_id}: "
                f"({location.latitude}, {location.longitude}) for {days_back} days"
            )

            response = await self.weather_service.get_weather_data(
                latitude=location.latitude,
                longitude=location.longitude,
                past_days=days_back,
                forecast_days=0,
                resolution_minutes=resolution_minutes,
                model="best_match",
            )

            if response.historical:
                df = pd.DataFrame([
                    {
                        "time": r.time,
                        "wind_speed": r.wind_speed,
                        "wind_speed_100m": r.wind_speed_100m,
                        "wind_direction": r.wind_direction,
                        "temperature": r.temperature,
                        "pressure": r.pressure,
                    }
                    for r in response.historical
                ])
                df["time"] = pd.to_datetime(df["time"], utc=True)
                weather_data[loc_id] = df
                logger.info(f"Got {len(df)} historical weather records for location {loc_id}")
            else:
                logger.warning(f"No historical weather data for location {loc_id}")

        return weather_data

    async def _load_wind_farm(self, wind_farm_id: int) -> WindFarm | None:
        """Load wind farm with all relationships."""
        result = await self.db.execute(
            select(WindFarm)
            .options(
                selectinload(WindFarm.wind_turbine_fleets)
                .selectinload(WindTurbineFleet.wind_turbine)
                .selectinload(WindTurbine.power_curve),
                selectinload(WindFarm.wind_turbine_fleets)
                .selectinload(WindTurbineFleet.location),
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

    async def _fetch_forecast_weather(
        self,
        locations: dict[int, Location],
        forecast_days: int,
        resolution_minutes: int,
        weather_model: str,
    ) -> dict[int, pd.DataFrame]:
        """Fetch forecast weather data for all locations."""
        weather_data = {}

        for loc_id, location in locations.items():
            logger.info(
                f"Fetching forecast weather for location {loc_id}: "
                f"({location.latitude}, {location.longitude}) using model {weather_model}"
            )

            response = await self.weather_service.get_weather_data(
                latitude=location.latitude,
                longitude=location.longitude,
                past_days=0,
                forecast_days=forecast_days,
                resolution_minutes=resolution_minutes,
                model=weather_model,
            )

            if response.forecast:
                # Convert to DataFrame
                df = pd.DataFrame([
                    {
                        "time": r.time,
                        "wind_speed": r.wind_speed,
                        "wind_speed_100m": r.wind_speed_100m,
                        "wind_direction": r.wind_direction,
                        "temperature": r.temperature,
                        "pressure": r.pressure,
                    }
                    for r in response.forecast
                ])
                df["time"] = pd.to_datetime(df["time"])
                weather_data[loc_id] = df
                logger.info(f"Got {len(df)} forecast weather records for location {loc_id}")
            else:
                logger.warning(f"No forecast weather data for location {loc_id}")

        return weather_data

    async def _calculate_forecasts(
        self,
        wind_farm: WindFarm,
        weather_data: dict[int, pd.DataFrame],
        granularity: GranularityEnum,
        weather_model: str,
        forecast_hours: int,
    ) -> list[WindGenerationForecast]:
        """Calculate power forecasts for each timestamp."""
        forecasts = []
        now = datetime.now(timezone.utc)

        # Get all unique timestamps from weather data
        all_times = set()
        for df in weather_data.values():
            all_times.update(df["time"].tolist())

        all_times = sorted(all_times)

        for timestamp in all_times:
            # Convert to timezone-aware datetime
            if isinstance(timestamp, pd.Timestamp):
                ts = timestamp.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

            # Skip if too far in future
            hours_ahead = (ts - now).total_seconds() / 3600
            if hours_ahead > forecast_hours or hours_ahead < 0:
                continue

            total_generation = 0.0
            wind_speeds: list[float] = []
            wind_directions: list[float] = []
            temperatures: list[float] = []

            for fleet in wind_farm.wind_turbine_fleets:
                # Get weather for this fleet's location
                if fleet.location_id not in weather_data:
                    continue

                weather_df = weather_data[fleet.location_id]
                weather_row = weather_df[weather_df["time"] == timestamp]

                if weather_row.empty:
                    continue

                # Get wind speed at hub height
                wind_speed = weather_row["wind_speed_100m"].iloc[0]
                if pd.isna(wind_speed):
                    wind_speed = weather_row["wind_speed"].iloc[0]

                if pd.isna(wind_speed):
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
                    total_generation += power_kw

            # Calculate averages
            avg_wind_speed = sum(wind_speeds) / len(wind_speeds) if wind_speeds else None
            avg_wind_dir = sum(wind_directions) / len(wind_directions) if wind_directions else None
            avg_temp = sum(temperatures) / len(temperatures) if temperatures else None

            forecast = WindGenerationForecast(
                wind_farm_id=wind_farm.id,
                forecast_time=ts,
                generation=round(total_generation, 2),
                granularity=granularity,
                wind_speed=round(avg_wind_speed, 2) if avg_wind_speed else None,
                wind_direction=round(avg_wind_dir, 1) if avg_wind_dir else None,
                temperature=round(avg_temp, 1) if avg_temp else None,
                weather_model=weather_model,
                forecast_horizon_hours=int(hours_ahead),
            )
            forecasts.append(forecast)

        return forecasts

    def _calculate_turbine_power(
        self,
        wind_speed: float,
        turbine: WindTurbine,
        num_turbines: int = 1,
    ) -> float:
        """Calculate power output for a turbine at given wind speed."""
        if wind_speed <= 0:
            return 0.0

        # Use power curve if available
        if turbine.power_curve and turbine.power_curve.wind_speed_value_map:
            power_curve = turbine.power_curve.wind_speed_value_map
            power_kw = self._interpolate_power_curve(wind_speed, power_curve)
        else:
            # Simplified power calculation
            cut_in = 3.0
            rated_speed = 12.0
            cut_out = 25.0
            nominal_power_kw = turbine.nominal_power * 1000

            if wind_speed < cut_in:
                power_kw = 0.0
            elif wind_speed < rated_speed:
                power_kw = nominal_power_kw * ((wind_speed - cut_in) / (rated_speed - cut_in)) ** 3
            elif wind_speed <= cut_out:
                power_kw = nominal_power_kw
            else:
                power_kw = 0.0

        return power_kw * num_turbines

    def _interpolate_power_curve(
        self,
        wind_speed: float,
        power_curve: dict[str, float],
    ) -> float:
        """Interpolate power from power curve."""
        points = [(float(k), v) for k, v in power_curve.items()]
        points.sort(key=lambda x: x[0])

        if not points:
            return 0.0

        speeds = [p[0] for p in points]
        powers = [p[1] for p in points]

        return float(np.interp(wind_speed, speeds, powers))

    async def _calculate_historical_forecasts(
        self,
        wind_farm: WindFarm,
        weather_data: dict[int, pd.DataFrame],
        granularity: GranularityEnum,
    ) -> list[WindGenerationForecast]:
        """Calculate power forecasts for historical timestamps."""
        forecasts = []

        # Get all unique timestamps from weather data
        all_times = set()
        for df in weather_data.values():
            all_times.update(df["time"].tolist())

        all_times = sorted(all_times)

        for timestamp in all_times:
            # Convert to timezone-aware datetime
            if isinstance(timestamp, pd.Timestamp):
                ts = timestamp.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

            total_generation = 0.0
            wind_speeds: list[float] = []
            wind_directions: list[float] = []
            temperatures: list[float] = []

            for fleet in wind_farm.wind_turbine_fleets:
                if fleet.location_id not in weather_data:
                    continue

                weather_df = weather_data[fleet.location_id]
                weather_row = weather_df[weather_df["time"] == timestamp]

                if weather_row.empty:
                    continue

                wind_speed = weather_row["wind_speed_100m"].iloc[0]
                if pd.isna(wind_speed):
                    wind_speed = weather_row["wind_speed"].iloc[0]

                if pd.isna(wind_speed):
                    continue

                wind_speeds.append(float(wind_speed))
                wind_dir = weather_row["wind_direction"].iloc[0]
                if not pd.isna(wind_dir):
                    wind_directions.append(float(wind_dir))
                temp = weather_row["temperature"].iloc[0]
                if not pd.isna(temp):
                    temperatures.append(float(temp))

                turbine = fleet.wind_turbine
                if turbine:
                    power_kw = self._calculate_turbine_power(
                        wind_speed=wind_speed,
                        turbine=turbine,
                        num_turbines=fleet.number_of_turbines,
                    )
                    total_generation += power_kw

            avg_wind_speed = sum(wind_speeds) / len(wind_speeds) if wind_speeds else None
            avg_wind_dir = sum(wind_directions) / len(wind_directions) if wind_directions else None
            avg_temp = sum(temperatures) / len(temperatures) if temperatures else None

            forecast = WindGenerationForecast(
                wind_farm_id=wind_farm.id,
                forecast_time=ts,
                generation=round(total_generation, 2),
                granularity=granularity,
                wind_speed=round(avg_wind_speed, 2) if avg_wind_speed else None,
                wind_direction=round(avg_wind_dir, 1) if avg_wind_dir else None,
                temperature=round(avg_temp, 1) if avg_temp else None,
                weather_model="historical",
                forecast_horizon_hours=0,  # Historical = 0 hours ahead
            )
            forecasts.append(forecast)

        return forecasts

    async def _delete_forecasts_in_range(
        self,
        wind_farm_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Delete forecasts for a wind farm within a time range."""
        stmt = delete(WindGenerationForecast).where(
            WindGenerationForecast.wind_farm_id == wind_farm_id,
            WindGenerationForecast.forecast_time >= start_time,
            WindGenerationForecast.forecast_time <= end_time,
        )
        result = await self.db.execute(stmt)
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} forecasts for wind farm {wind_farm_id} "
                f"from {start_time} to {end_time}"
            )

        return deleted_count

    async def _delete_old_forecasts(self, wind_farm_id: int) -> int:
        """Delete old forecasts for a wind farm."""
        stmt = delete(WindGenerationForecast).where(
            WindGenerationForecast.wind_farm_id == wind_farm_id
        )
        result = await self.db.execute(stmt)
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old forecasts for wind farm {wind_farm_id}")

        return deleted_count

    async def _save_forecasts(
        self,
        forecasts: list[WindGenerationForecast],
    ) -> int:
        """Save forecast records to database."""
        if not forecasts:
            return 0

        self.db.add_all(forecasts)
        await self.db.flush()

        logger.info(f"Saved {len(forecasts)} forecast records")
        return len(forecasts)

    async def get_latest_forecasts(
        self,
        wind_farm_id: int,
        limit: int = 1000,
    ) -> list[WindGenerationForecast]:
        """Get latest forecasts for a wind farm."""
        result = await self.db.execute(
            select(WindGenerationForecast)
            .where(WindGenerationForecast.wind_farm_id == wind_farm_id)
            .order_by(WindGenerationForecast.forecast_time)
            .limit(limit)
        )
        return list(result.scalars().all())

