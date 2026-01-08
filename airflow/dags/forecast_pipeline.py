"""Wind Generation Forecast Pipeline DAG.

This DAG runs periodically to generate power forecasts for all wind farms
using Open-Meteo weather forecasts and the configured wind farm models.
"""

import os
from datetime import datetime, timedelta

import requests
from airflow.operators.python import PythonOperator

from airflow import DAG

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://app:8000")

# Default DAG arguments
default_args = {
    "owner": "koppen",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def get_auth_token() -> str:
    """Get authentication token from the API.

    For production, use a service account or API key.
    For MVP, we'll use a default user.
    """
    # Try to login with default credentials
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            data={
                "username": "forecast-service@koppen.local",
                "password": "forecast-service-password",
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.json().get("access_token", "")
    except Exception as e:
        print(f"Failed to get auth token: {e}")
    return ""


def get_wind_farms(token: str) -> list[dict]:
    """Fetch all wind farms from the API."""
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = requests.get(
            f"{API_BASE_URL}/api/v1/wind-farms/",
            headers=headers,
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Failed to fetch wind farms: {e}")
    return []


def generate_forecast_for_farm(
    wind_farm_id: int,
    token: str,
    forecast_hours: int = 48,
    weather_model: str = "best_match",
) -> dict:
    """Generate forecast for a single wind farm."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/forecasts/generate",
            headers=headers,
            json={
                "wind_farm_id": wind_farm_id,
                "forecast_hours": forecast_hours,
                "granularity": "60min",
                "weather_model": weather_model,
            },
            timeout=120,  # Forecast generation can take time
        )

        if response.status_code in (200, 202):
            result = response.json()
            print(
                f"✓ Wind farm {wind_farm_id}: Created {result.get('records_created', 0)} forecast records"
            )
            return result
        else:
            print(
                f"✗ Wind farm {wind_farm_id}: Failed with status {response.status_code}"
            )
            print(f"  Response: {response.text}")
            return {"error": response.text}

    except Exception as e:
        print(f"✗ Wind farm {wind_farm_id}: Exception - {e}")
        return {"error": str(e)}


def run_forecast_pipeline(**context) -> None:
    """Main forecast pipeline task.

    Fetches all wind farms and generates forecasts for each one.
    """
    print("=" * 60)
    print("Starting Wind Generation Forecast Pipeline")
    print(f"Execution time: {context.get('execution_date', datetime.now())}")
    print("=" * 60)

    # Get authentication token
    token = get_auth_token()
    if not token:
        print("Warning: Running without authentication token")

    # Fetch all wind farms
    wind_farms = get_wind_farms(token)

    if not wind_farms:
        print("No wind farms found. Exiting.")
        return

    print(f"Found {len(wind_farms)} wind farm(s)")

    # Configuration
    forecast_hours = 48  # 2 days ahead
    weather_model = "best_match"  # Open-Meteo best match

    # Generate forecasts for each wind farm
    results = []
    for farm in wind_farms:
        farm_id = farm.get("id")
        farm_name = farm.get("name", "Unknown")

        print(f"\n--- Processing: {farm_name} (ID: {farm_id}) ---")

        result = generate_forecast_for_farm(
            wind_farm_id=farm_id,
            token=token,
            forecast_hours=forecast_hours,
            weather_model=weather_model,
        )
        results.append(
            {
                "farm_id": farm_id,
                "farm_name": farm_name,
                "result": result,
            }
        )

    # Summary
    print("\n" + "=" * 60)
    print("Pipeline Summary")
    print("=" * 60)

    successful = sum(1 for r in results if "error" not in r["result"])
    failed = len(results) - successful
    total_records = sum(
        r["result"].get("records_created", 0)
        for r in results
        if "error" not in r["result"]
    )

    print(f"Wind Farms Processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total Forecast Records Created: {total_records}")
    print("=" * 60)


# Create the DAG
with DAG(
    dag_id="wind_generation_forecast",
    default_args=default_args,
    description="Generate wind power forecasts for all wind farms",
    schedule_interval="0 */6 * * *",  # Every 6 hours
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["forecasting", "wind-power", "koppen"],
) as dag:
    # Main forecast task
    forecast_task = PythonOperator(
        task_id="generate_forecasts",
        python_callable=run_forecast_pipeline,
        provide_context=True,
    )
