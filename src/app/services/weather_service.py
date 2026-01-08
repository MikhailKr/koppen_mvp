"""Weather service for Open-Meteo API integration."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)


@dataclass
class WeatherRecord:
    """Single weather data point."""

    time: datetime
    temperature: float | None = None
    temperature_80m: float | None = None
    wind_speed: float | None = None
    wind_speed_80m: float | None = None
    wind_speed_100m: float | None = None
    wind_direction: float | None = None
    wind_direction_80m: float | None = None
    wind_direction_100m: float | None = None
    pressure: float | None = None
    precipitation: float | None = None
    cloud_cover: float | None = None


@dataclass
class WeatherResponse:
    """Weather API response."""

    historical: list[WeatherRecord] = field(default_factory=list)
    forecast: list[WeatherRecord] = field(default_factory=list)
    model_used: str | None = None
    resolution_info: str | None = None
    latitude: float | None = None
    longitude: float | None = None


# Available weather models in Open-Meteo
WEATHER_MODELS: dict[str, str] = {
    "icon_d2": "ICON-D2 (15min, Central Europe)",
    "icon_global": "ICON Global",
    "ecmwf_ifs04": "ECMWF IFS",
    "gfs_seamless": "GFS (NOAA)",
    "best_match": "Best Match (Auto)",
    "meteofrance_arpege_seamless": "Météo-France ARPEGE",
    "jma_seamless": "JMA (Japan)",
    "gem_seamless": "GEM (Canada)",
}

# Resolution options (minutes)
RESOLUTION_OPTIONS: list[int] = [15, 30, 60]


class WeatherService:
    """Service for fetching weather data from Open-Meteo API."""

    BASE_URL_FORECAST = "https://api.open-meteo.com/v1/forecast"
    BASE_URL_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

    # Variables for forecast API (more variables available)
    FORECAST_VARS = [
        "temperature_2m",
        "wind_speed_10m",
        "wind_speed_80m",
        "wind_speed_100m",
        "wind_direction_10m",
        "wind_direction_80m",
        "wind_direction_100m",
        "temperature_80m",
        "pressure_msl",
        "precipitation",
        "cloud_cover",
    ]

    # Variables for archive API (limited set)
    ARCHIVE_VARS = [
        "temperature_2m",
        "wind_speed_10m",
        "wind_speed_100m",
        "wind_direction_10m",
        "wind_direction_100m",
        "pressure_msl",
        "precipitation",
        "cloud_cover",
    ]

    def __init__(self, timeout: int = 30) -> None:
        """Initialize the weather service.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

    async def get_weather_data(
        self,
        latitude: float,
        longitude: float,
        model: str = "icon_global",
        past_days: int = 7,
        forecast_days: int = 7,
        resolution_minutes: int = 60,
    ) -> WeatherResponse:
        """Fetch weather data from Open-Meteo API.

        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            model: Weather model to use.
            past_days: Number of historical days to fetch.
            forecast_days: Number of forecast days to fetch.
            resolution_minutes: Forecast resolution (15, 30, or 60 minutes).

        Returns:
            WeatherResponse object containing historical and forecast data.
        """
        historical = await self._fetch_historical(
            latitude=latitude,
            longitude=longitude,
            past_days=past_days,
        )

        forecast, model_used, resolution_info = await self._fetch_forecast(
            latitude=latitude,
            longitude=longitude,
            model=model,
            forecast_days=forecast_days,
            resolution_minutes=resolution_minutes,
        )

        return WeatherResponse(
            historical=historical,
            forecast=forecast,
            model_used=model_used,
            resolution_info=resolution_info,
            latitude=latitude,
            longitude=longitude,
        )

    async def _fetch_historical(
        self,
        latitude: float,
        longitude: float,
        past_days: int,
    ) -> list[WeatherRecord]:
        """Fetch historical weather data.

        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            past_days: Number of historical days.

        Returns:
            List of WeatherRecord objects.
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=past_days)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "hourly": ",".join(self.ARCHIVE_VARS),
            "wind_speed_unit": "ms",
            "timezone": "auto",
        }

        url = f"{self.BASE_URL_ARCHIVE}?" + "&".join(
            f"{k}={v}" for k, v in params.items()
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"Historical API returned {response.status_code}")
                return []

            data = response.json()
            if "hourly" not in data:
                return []

            return self._parse_hourly_data(data["hourly"])

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return []

    async def _fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        model: str,
        forecast_days: int,
        resolution_minutes: int,
    ) -> tuple[list[WeatherRecord], str | None, str | None]:
        """Fetch forecast weather data.

        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            model: Weather model to use.
            forecast_days: Number of forecast days.
            resolution_minutes: Resolution in minutes (15, 30, or 60).

        Returns:
            Tuple of (records, model_used, resolution_info).
        """
        params: dict[str, str | int | float] = {
            "latitude": latitude,
            "longitude": longitude,
            "wind_speed_unit": "ms",
            "timezone": "auto",
        }

        resolution_info: str | None = None

        if resolution_minutes == 15:
            # Use ICON-D2 model with native 15-minute data
            params["minutely_15"] = ",".join(self.FORECAST_VARS)
            params["models"] = "icon_d2"
            params["forecast_minutely_15"] = 96  # 24 hours of 15-min data
            resolution_info = "15-min native data (ICON-D2)"
            logger.info("Using native 15-minute forecast data from Open-Meteo (ICON-D2)")
        elif resolution_minutes == 30:
            params["hourly"] = ",".join(self.FORECAST_VARS)
            params["models"] = model
            params["forecast_days"] = forecast_days
            resolution_info = "30-min (hourly interpolated)"
            logger.info("Using 30-minute forecast (hourly will be interpolated)")
        else:
            params["hourly"] = ",".join(self.FORECAST_VARS)
            params["models"] = model
            params["forecast_days"] = forecast_days
            resolution_info = "60-min (hourly)"
            logger.info("Using 60-minute (hourly) forecast")

        url = f"{self.BASE_URL_FORECAST}?" + "&".join(
            f"{k}={v}" for k, v in params.items()
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"Forecast API returned {response.status_code}")
                return [], None, None

            data = response.json()
            model_used = model

            # Check for minutely_15 data first (for 15-min resolution)
            if "minutely_15" in data and data["minutely_15"]:
                records = self._parse_hourly_data(data["minutely_15"])
                resolution_info = "15-min native (ICON-D2)"
                return records, model_used, resolution_info

            # Fall back to hourly data
            if "hourly" in data and data["hourly"]:
                records = self._parse_hourly_data(data["hourly"])

                # Interpolate to 30-min if requested
                if resolution_minutes == 30 and records:
                    records = self._interpolate_to_30min(records)
                    resolution_info = "30-min (interpolated)"

                return records, model_used, resolution_info

            return [], None, None

        except Exception as e:
            logger.error(f"Failed to fetch forecast data: {e}")
            return [], None, None

    def _parse_hourly_data(self, hourly_data: dict) -> list[WeatherRecord]:
        """Parse hourly data from API response.

        Args:
            hourly_data: Hourly data dictionary from API response.

        Returns:
            List of WeatherRecord objects.
        """
        times = hourly_data.get("time", [])
        records = []

        for i, time_str in enumerate(times):
            records.append(
                WeatherRecord(
                    time=datetime.fromisoformat(time_str),
                    temperature=self._get_value(hourly_data, "temperature_2m", i),
                    temperature_80m=self._get_value(hourly_data, "temperature_80m", i),
                    wind_speed=self._get_value(hourly_data, "wind_speed_10m", i),
                    wind_speed_80m=self._get_value(hourly_data, "wind_speed_80m", i),
                    wind_speed_100m=self._get_value(hourly_data, "wind_speed_100m", i),
                    wind_direction=self._get_value(hourly_data, "wind_direction_10m", i),
                    wind_direction_80m=self._get_value(hourly_data, "wind_direction_80m", i),
                    wind_direction_100m=self._get_value(hourly_data, "wind_direction_100m", i),
                    pressure=self._get_value(hourly_data, "pressure_msl", i),
                    precipitation=self._get_value(hourly_data, "precipitation", i),
                    cloud_cover=self._get_value(hourly_data, "cloud_cover", i),
                )
            )

        return records

    @staticmethod
    def _get_value(data: dict, key: str, index: int) -> float | None:
        """Safely get value from data list."""
        values = data.get(key)
        if values and index < len(values):
            return values[index]
        return None

    def _interpolate_to_30min(self, records: list[WeatherRecord]) -> list[WeatherRecord]:
        """Interpolate hourly data to 30-minute intervals.

        Args:
            records: List of hourly records.

        Returns:
            List of 30-minute interpolated records.
        """
        if len(records) < 2:
            return records

        interpolated = []

        for i in range(len(records) - 1):
            current = records[i]
            next_rec = records[i + 1]

            # Add current record
            interpolated.append(current)

            # Add interpolated record at midpoint
            mid_time = current.time + timedelta(minutes=30)
            interpolated.append(
                WeatherRecord(
                    time=mid_time,
                    temperature=self._interpolate_value(current.temperature, next_rec.temperature),
                    temperature_80m=self._interpolate_value(current.temperature_80m, next_rec.temperature_80m),
                    wind_speed=self._interpolate_value(current.wind_speed, next_rec.wind_speed),
                    wind_speed_80m=self._interpolate_value(current.wind_speed_80m, next_rec.wind_speed_80m),
                    wind_speed_100m=self._interpolate_value(current.wind_speed_100m, next_rec.wind_speed_100m),
                    wind_direction=self._interpolate_value(current.wind_direction, next_rec.wind_direction),
                    wind_direction_80m=self._interpolate_value(current.wind_direction_80m, next_rec.wind_direction_80m),
                    wind_direction_100m=self._interpolate_value(current.wind_direction_100m, next_rec.wind_direction_100m),
                    pressure=self._interpolate_value(current.pressure, next_rec.pressure),
                    precipitation=self._interpolate_value(current.precipitation, next_rec.precipitation),
                    cloud_cover=self._interpolate_value(current.cloud_cover, next_rec.cloud_cover),
                )
            )

        # Add last record
        interpolated.append(records[-1])
        return interpolated

    @staticmethod
    def _interpolate_value(v1: float | None, v2: float | None) -> float | None:
        """Interpolate between two values."""
        if v1 is None or v2 is None:
            return v1 or v2
        return (v1 + v2) / 2

    @staticmethod
    def get_available_models() -> dict[str, str]:
        """Get available weather models."""
        return WEATHER_MODELS.copy()

    @staticmethod
    def get_resolution_options() -> list[int]:
        """Get available resolution options in minutes."""
        return RESOLUTION_OPTIONS.copy()

    @staticmethod
    def get_model_for_resolution(resolution_minutes: int) -> str | None:
        """Get required model for a specific resolution."""
        if resolution_minutes == 15:
            return "icon_d2"
        return None

