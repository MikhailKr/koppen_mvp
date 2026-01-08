"""API client for backend communication."""

import httpx
import streamlit as st

from frontend.config import API_BASE_URL, API_V1_PREFIX


class APIClient:
    """HTTP client for backend API."""

    def __init__(self, token: str | None = None):
        """Initialize API client.

        Args:
            token: JWT access token for authenticated requests.
        """
        self.base_url = f"{API_BASE_URL}{API_V1_PREFIX}"
        self.token = token

    @property
    def headers(self) -> dict[str, str]:
        """Get request headers with optional auth token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def login(self, email: str, password: str) -> dict | None:
        """Login and get access token.

        Args:
            email: User email.
            password: User password.

        Returns:
            Token response or None if login failed.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/auth/login",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code == 200:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    def register(
        self, email: str, password: str, full_name: str | None = None
    ) -> dict | None:
        """Register a new user.

        Args:
            email: User email.
            password: User password.
            full_name: Optional full name.

        Returns:
            User data or None if registration failed.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/auth/register",
                json={"email": email, "password": password, "full_name": full_name},
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 201:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    def get_current_user(self) -> dict | None:
        """Get current authenticated user."""
        try:
            response = httpx.get(f"{self.base_url}/auth/me", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    def get_locations(self) -> list[dict]:
        """Get all locations."""
        try:
            response = httpx.get(f"{self.base_url}/locations/", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    def create_location(self, latitude: float, longitude: float) -> dict | None:
        """Create a new location."""
        try:
            response = httpx.post(
                f"{self.base_url}/locations/",
                json={"latitude": latitude, "longitude": longitude},
                headers=self.headers,
            )
            if response.status_code == 201:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    def delete_location(self, location_id: int) -> bool:
        """Delete a location."""
        try:
            response = httpx.delete(
                f"{self.base_url}/locations/{location_id}",
                headers=self.headers,
            )
            return response.status_code == 204
        except httpx.RequestError:
            return False

    def get_wind_farms(self) -> list[dict]:
        """Get all wind farms for current user."""
        try:
            response = httpx.get(f"{self.base_url}/wind-farms/", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    def create_wind_farm(
        self, name: str, description: str | None = None
    ) -> dict | None:
        """Create a new wind farm."""
        try:
            response = httpx.post(
                f"{self.base_url}/wind-farms/",
                json={"name": name, "description": description},
                headers=self.headers,
            )
            if response.status_code == 201:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    def delete_wind_farm(self, wind_farm_id: int) -> dict:
        """Delete a wind farm. Returns dict with success status and any error message."""
        try:
            response = httpx.delete(
                f"{self.base_url}/wind-farms/{wind_farm_id}",
                headers=self.headers,
                timeout=30.0,
            )
            if response.status_code in (200, 204):
                return {"success": True}
            elif response.status_code == 401:
                return {"success": False, "error": "Authentication required"}
            elif response.status_code == 404:
                return {"success": False, "error": "Farm not found"}
            else:
                return {
                    "success": False,
                    "error": f"Server error: {response.status_code}",
                }
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}

    # Power Curves
    def get_power_curves(self) -> list[dict]:
        """Get all power curves."""
        try:
            response = httpx.get(f"{self.base_url}/power-curves/", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    def create_power_curve(
        self, name: str | None, wind_speed_value_map: dict[str, float]
    ) -> dict | None:
        """Create a new power curve."""
        try:
            response = httpx.post(
                f"{self.base_url}/power-curves/",
                json={"name": name, "wind_speed_value_map": wind_speed_value_map},
                headers=self.headers,
            )
            if response.status_code == 201:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    def delete_power_curve(self, power_curve_id: int) -> bool:
        """Delete a power curve."""
        try:
            response = httpx.delete(
                f"{self.base_url}/power-curves/{power_curve_id}",
                headers=self.headers,
            )
            return response.status_code == 204
        except httpx.RequestError:
            return False

    # Wind Turbines
    def get_wind_turbines(self) -> list[dict]:
        """Get all wind turbines."""
        try:
            response = httpx.get(
                f"{self.base_url}/wind-turbines/", headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    def create_wind_turbine(
        self,
        turbine_type: str | None = None,
        hub_height: float = 100.0,
        nominal_power: float = 1.0,
        power_curve_id: int | None = None,
    ) -> dict | None:
        """Create a new wind turbine specification (reusable template)."""
        try:
            payload = {
                "turbine_type": turbine_type,
                "hub_height": hub_height,
                "nominal_power": nominal_power,
            }
            if power_curve_id is not None:
                payload["power_curve_id"] = power_curve_id

            response = httpx.post(
                f"{self.base_url}/wind-turbines/",
                json=payload,
                headers=self.headers,
            )
            if response.status_code == 201:
                return response.json()
            return {
                "error": True,
                "status": response.status_code,
                "detail": response.text,
            }
        except httpx.RequestError as e:
            return {"error": True, "detail": str(e)}

    def delete_wind_turbine(self, turbine_id: int) -> bool:
        """Delete a wind turbine."""
        try:
            response = httpx.delete(
                f"{self.base_url}/wind-turbines/{turbine_id}",
                headers=self.headers,
            )
            return response.status_code == 204
        except httpx.RequestError:
            return False

    # Fleets
    def get_fleets(self, wind_farm_id: int | None = None) -> list[dict]:
        """Get all fleets, optionally filtered by wind farm."""
        try:
            url = f"{self.base_url}/fleets/"
            if wind_farm_id:
                url += f"?wind_farm_id={wind_farm_id}"
            response = httpx.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    def create_fleet(
        self,
        wind_farm_id: int,
        wind_turbine_id: int,
        location_id: int,
        number_of_turbines: int = 1,
    ) -> dict | None:
        """Create a new fleet (link turbine spec to location in a farm)."""
        try:
            response = httpx.post(
                f"{self.base_url}/fleets/",
                json={
                    "wind_farm_id": wind_farm_id,
                    "wind_turbine_id": wind_turbine_id,
                    "location_id": location_id,
                    "number_of_turbines": number_of_turbines,
                },
                headers=self.headers,
            )
            if response.status_code == 201:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    def delete_fleet(self, fleet_id: int) -> bool:
        """Delete a fleet."""
        try:
            response = httpx.delete(
                f"{self.base_url}/fleets/{fleet_id}",
                headers=self.headers,
            )
            return response.status_code == 204
        except httpx.RequestError:
            return False

    # Weather API
    def get_weather_data(
        self,
        latitude: float,
        longitude: float,
        model: str = "icon_global",
        past_days: int = 7,
        forecast_days: int = 7,
        resolution_minutes: int = 60,
    ) -> dict | None:
        """Get weather data for a location.

        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            model: Weather model to use.
            past_days: Number of historical days.
            forecast_days: Number of forecast days.
            resolution_minutes: Resolution (15, 30, 60 minutes).

        Returns:
            Weather data dict or None if request failed.
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "model": model,
                "past_days": past_days,
                "forecast_days": forecast_days,
                "resolution_minutes": resolution_minutes,
            }
            response = httpx.get(
                f"{self.base_url}/weather/",
                params=params,
                headers=self.headers,
                timeout=60.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data
            # Log error for debugging
            print(f"Weather API error: {response.status_code} - {response.text[:200]}")
            return None
        except httpx.RequestError as e:
            print(f"Weather API request error: {e}")
            return None

    def get_weather_models(self) -> dict[str, str]:
        """Get available weather models.

        Returns:
            Dictionary mapping model codes to display names.
        """
        try:
            response = httpx.get(
                f"{self.base_url}/weather/models", headers=self.headers
            )
            if response.status_code == 200:
                return response.json().get("models", {})
            return {}
        except httpx.RequestError:
            return {}

    def get_weather_resolutions(self) -> list[int]:
        """Get available weather resolutions.

        Returns:
            List of available resolutions in minutes.
        """
        try:
            response = httpx.get(
                f"{self.base_url}/weather/resolutions", headers=self.headers
            )
            if response.status_code == 200:
                return response.json().get("resolutions", [60])
            return [60]
        except httpx.RequestError:
            return [60]

    # Synthetic Generation API
    def generate_synthetic_data(
        self,
        wind_farm_id: int,
        days_back: int = 30,
        granularity: str = "60min",
        add_noise: bool = False,
        noise_std_percent: float = 5.0,
        random_outages: bool = False,
        outage_probability: float = 0.01,
        outage_duration_hours: int = 4,
    ) -> dict | None:
        """Generate synthetic wind generation data for a wind farm."""
        try:
            response = httpx.post(
                f"{self.base_url}/synthetic/generate",
                json={
                    "wind_farm_id": wind_farm_id,
                    "days_back": days_back,
                    "granularity": granularity,
                    "add_noise": add_noise,
                    "noise_std_percent": noise_std_percent,
                    "random_outages": random_outages,
                    "outage_probability": outage_probability,
                    "outage_duration_hours": outage_duration_hours,
                },
                headers=self.headers,
                timeout=120.0,  # Long timeout for generation
            )
            if response.status_code == 201:
                return response.json()
            return {
                "error": True,
                "status": response.status_code,
                "detail": response.text,
            }
        except httpx.RequestError as e:
            return {"error": True, "detail": str(e)}

    def get_farm_generation_records(
        self,
        wind_farm_id: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 5000,
    ) -> list[dict]:
        """Get wind farm generation records.

        Args:
            wind_farm_id: Filter by wind farm ID.
            start_time: Filter by start time (ISO format string).
            end_time: Filter by end time (ISO format string).
            limit: Maximum number of records to return.

        Returns:
            List of generation record dicts.
        """
        try:
            params: dict = {"limit": limit}
            if wind_farm_id:
                params["wind_farm_id"] = wind_farm_id
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            response = httpx.get(
                f"{self.base_url}/farm-generation-records/",
                params=params,
                headers=self.headers,
                timeout=30.0,
            )
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    # ==================== Forecast Methods ====================

    def generate_forecast(
        self,
        wind_farm_id: int,
        forecast_hours: int = 48,
        granularity: str = "60min",
        weather_model: str = "best_match",
    ) -> dict:
        """Generate forecast for a wind farm."""
        try:
            response = httpx.post(
                f"{self.base_url}/forecasts/generate",
                json={
                    "wind_farm_id": wind_farm_id,
                    "forecast_hours": forecast_hours,
                    "granularity": granularity,
                    "weather_model": weather_model,
                },
                headers=self.headers,
                timeout=120.0,
            )
            return response.json()
        except httpx.RequestError as e:
            return {"error": str(e)}

    def generate_historical_forecast(
        self,
        wind_farm_id: int,
        days_back: int = 30,
        granularity: str = "min_60",
    ) -> dict:
        """Generate historical forecast for a wind farm using past weather data."""
        try:
            response = httpx.post(
                f"{self.base_url}/forecasts/generate-historical",
                json={
                    "wind_farm_id": wind_farm_id,
                    "days_back": days_back,
                    "granularity": granularity,
                },
                headers=self.headers,
                timeout=180.0,  # Historical can take longer
            )
            return response.json()
        except httpx.RequestError as e:
            return {"error": str(e)}

    def get_forecasts(
        self,
        wind_farm_id: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Get forecast records."""
        try:
            params: dict = {"limit": limit}
            if wind_farm_id:
                params["wind_farm_id"] = wind_farm_id
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            response = httpx.get(
                f"{self.base_url}/forecasts/",
                params=params,
                headers=self.headers,
                timeout=30.0,
            )
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    def get_forecast_runs(
        self,
        wind_farm_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get forecast pipeline runs."""
        try:
            params: dict = {"limit": limit}
            if wind_farm_id:
                params["wind_farm_id"] = wind_farm_id
            response = httpx.get(
                f"{self.base_url}/forecasts/runs",
                params=params,
                headers=self.headers,
                timeout=30.0,
            )
            if response.status_code == 200:
                return response.json()
            return []
        except httpx.RequestError:
            return []

    def request_forecast(
        self,
        wind_farm_id: int,
        horizon_hours: int = 48,
        start_hours_from_now: int = 0,
        granularity: str = "60min",
    ) -> list[dict]:
        """Request forecast data for a wind farm.

        Args:
            wind_farm_id: The ID of the wind farm
            horizon_hours: Forecast horizon in hours (1-168)
            start_hours_from_now: Start offset in hours from now (0-168)
            granularity: Time resolution - "15min", "30min", or "60min"

        Returns:
            List of forecast records
        """
        try:
            params: dict = {
                "horizon_hours": horizon_hours,
                "start_hours_from_now": start_hours_from_now,
                "granularity": granularity,
            }
            response = httpx.get(
                f"{self.base_url}/forecasts/request/{wind_farm_id}",
                params=params,
                headers=self.headers,
                timeout=120.0,  # Longer timeout for forecast generation
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return []
            else:
                error_msg = response.text
                raise Exception(f"API error {response.status_code}: {error_msg}")
        except httpx.RequestError as e:
            raise Exception(f"Connection error: {str(e)}")

    def chat(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        """Send a message to the AI agent.

        Args:
            message: The user's message.
            conversation_history: Previous messages in the conversation.

        Returns:
            Response from the AI agent.
        """
        try:
            payload = {
                "message": message,
                "conversation_history": conversation_history or [],
            }
            response = httpx.post(
                f"{self.base_url}/chat/",
                json=payload,
                headers=self.headers,
                timeout=120.0,  # Longer timeout for AI responses
            )
            if response.status_code == 200:
                return response.json()
            return {"response": f"Error: {response.status_code}", "success": False}
        except httpx.RequestError as e:
            return {"response": f"Connection error: {str(e)}", "success": False}


def get_api_client() -> APIClient:
    """Get API client with current session token."""
    token = st.session_state.get("token")
    return APIClient(token=token)
