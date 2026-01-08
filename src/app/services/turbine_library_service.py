"""Service to import wind turbine data from windpowerlib's database."""

import logging
import warnings

import pandas as pd
import requests
import urllib3

logger = logging.getLogger(__name__)

# Suppress SSL warnings when using verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OEDB_URL = (
    "https://oep.iks.cs.ovgu.de/api/v0/schema/supply/tables/wind_turbine_library/rows/"
)


def fetch_turbine_data_from_oedb() -> pd.DataFrame:
    """Fetch turbine data from OEDB with SSL verification disabled.

    Returns:
        DataFrame with turbine data.
    """
    try:
        # Disable SSL verification for this problematic server
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.get(OEDB_URL, verify=False, timeout=60)

        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Failed to fetch turbine data from OEDB: {e}")
        raise


def import_wind_turbine_library() -> list[tuple[dict, dict]]:
    """Import turbine data from Open Energy Database.

    Returns:
        List of tuples: (power_curve_dict, turbine_data_dict)
    """
    turbines = fetch_turbine_data_from_oedb()
    dict_turbines = turbines.to_dict("records")
    model_data: list[tuple[dict, dict]] = []

    for turbine_data in dict_turbines:
        try:
            # Parse power curve data
            power_curve_speeds = turbine_data.get("power_curve_wind_speeds")
            power_curve_values = turbine_data.get("power_curve_values")

            if not power_curve_speeds or not power_curve_values:
                continue

            # Handle string or list format
            if isinstance(power_curve_speeds, str):
                wind_speed = [str(s) for s in eval(power_curve_speeds)]
            else:
                wind_speed = [str(s) for s in power_curve_speeds]

            if isinstance(power_curve_values, str):
                power = eval(power_curve_values)
            else:
                power = power_curve_values

            power_curve = dict(zip(wind_speed, power, strict=False))

            # Parse hub height
            hub_height_raw = turbine_data.get("hub_height", "100")
            if isinstance(hub_height_raw, str):
                hub_height = float(hub_height_raw.split(";")[0])
            elif isinstance(hub_height_raw, (int, float)):
                hub_height = float(hub_height_raw)
            else:
                hub_height = 100.0

            # Parse nominal power (in kW, convert to MW)
            nominal_power_kw = turbine_data.get("nominal_power", 1000)
            nominal_power_mw = nominal_power_kw / 1000.0

            turbine_d = {
                "hub_height": hub_height,
                "turbine_type": turbine_data.get("turbine_type", "Unknown"),
                "nominal_power": nominal_power_mw,
            }
            model_data.append((power_curve, turbine_d))
        except Exception as e:
            logger.debug(f"Skipping turbine due to error: {e}")
            continue

    logger.info(f"Parsed {len(model_data)} turbines from OEDB")
    return model_data
