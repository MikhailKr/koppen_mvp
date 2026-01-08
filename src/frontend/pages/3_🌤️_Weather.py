"""Weather observation and forecast page - Presentation layer only."""

import altair as alt
import pandas as pd
import streamlit as st

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.styles import inject_css


# ==================== CHART HELPER FUNCTIONS ====================
def render_combined_chart(
    hist_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    column: str,
    y_title: str,
    hist_color: str = "#1f77b4",
    forecast_color: str = "#ff7f0e",
    y_domain: list | None = None,
) -> alt.Chart | None:
    """Render a combined chart with historical (solid) and forecast (dotted) data."""
    charts = []

    y_scale = alt.Scale(domain=y_domain) if y_domain else alt.Scale()

    # Historical data - solid line
    if not hist_df.empty and column in hist_df.columns:
        hist_data = hist_df[["time", column]].dropna()
        if not hist_data.empty:
            hist_chart = (
                alt.Chart(hist_data)
                .mark_line(
                    strokeWidth=2,
                    color=hist_color,
                )
                .encode(
                    x=alt.X("time:T", title="Time"),
                    y=alt.Y(f"{column}:Q", title=y_title, scale=y_scale),
                    tooltip=[
                        alt.Tooltip("time:T", title="Time"),
                        alt.Tooltip(f"{column}:Q", title=y_title, format=".2f"),
                    ],
                )
            )
            charts.append(hist_chart)

    # Forecast data - dotted line
    if not forecast_df.empty and column in forecast_df.columns:
        forecast_data = forecast_df[["time", column]].dropna()
        if not forecast_data.empty:
            forecast_chart = (
                alt.Chart(forecast_data)
                .mark_line(
                    strokeWidth=2,
                    strokeDash=[5, 5],
                    color=forecast_color,
                )
                .encode(
                    x=alt.X("time:T", title="Time"),
                    y=alt.Y(f"{column}:Q", title=y_title, scale=y_scale),
                    tooltip=[
                        alt.Tooltip("time:T", title="Time"),
                        alt.Tooltip(f"{column}:Q", title=y_title, format=".2f"),
                    ],
                )
            )
            charts.append(forecast_chart)

    if not charts:
        return None

    # Combine charts
    combined = charts[0]
    for chart in charts[1:]:
        combined = combined + chart

    return combined.properties(height=400).interactive()


def records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    """Convert weather records from API to DataFrame."""
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])

    # Convert numeric columns to proper dtype
    numeric_cols = [
        "temperature",
        "temperature_80m",
        "wind_speed",
        "wind_speed_80m",
        "wind_speed_100m",
        "wind_direction",
        "wind_direction_80m",
        "wind_direction_100m",
        "pressure",
        "precipitation",
        "cloud_cover",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ==================== AVAILABLE PARAMETERS ====================
WEATHER_PARAMS = {
    "wind_speed": {
        "label": "Wind Speed @ 10m (m/s)",
        "hist_color": "#1f77b4",
        "forecast_color": "#aec7e8",
    },
    "wind_speed_80m": {
        "label": "Wind Speed @ 80m (m/s)",
        "hist_color": "#2ca02c",
        "forecast_color": "#98df8a",
    },
    "wind_speed_100m": {
        "label": "Wind Speed @ 100m (m/s)",
        "hist_color": "#17becf",
        "forecast_color": "#9edae5",
    },
    "wind_direction": {
        "label": "Wind Direction @ 10m (°)",
        "hist_color": "#9467bd",
        "forecast_color": "#c5b0d5",
        "domain": [0, 360],
    },
    "wind_direction_80m": {
        "label": "Wind Direction @ 80m (°)",
        "hist_color": "#e377c2",
        "forecast_color": "#f7b6d2",
        "domain": [0, 360],
    },
    "wind_direction_100m": {
        "label": "Wind Direction @ 100m (°)",
        "hist_color": "#bcbd22",
        "forecast_color": "#dbdb8d",
        "domain": [0, 360],
    },
    "temperature": {
        "label": "Temperature @ 2m (°C)",
        "hist_color": "#ff7f0e",
        "forecast_color": "#ffbb78",
    },
    "temperature_80m": {
        "label": "Temperature @ 80m (°C)",
        "hist_color": "#d62728",
        "forecast_color": "#ff9896",
    },
    "pressure": {
        "label": "Pressure MSL (hPa)",
        "hist_color": "#8c564b",
        "forecast_color": "#c49c94",
    },
    "precipitation": {
        "label": "Precipitation (mm)",
        "hist_color": "#7f7f7f",
        "forecast_color": "#c7c7c7",
    },
    "cloud_cover": {
        "label": "Cloud Cover (%)",
        "hist_color": "#1f77b4",
        "forecast_color": "#aec7e8",
        "domain": [0, 100],
    },
}


# ==================== PAGE SETUP ====================
st.set_page_config(
    page_title="Weather - Koppen",
    page_icon="⚡",
    layout="wide",
)

init_session_state()

inject_css()
render_sidebar()
require_auth()

st.title("🌤️ Weather Data")
st.caption("View historical weather and forecasts for your locations")

# Initialize API client
api = get_api_client()

# Load locations
with st.spinner("Loading locations..."):
    locations = api.get_locations()

if not locations:
    st.warning(
        "⚠️ No locations found. Please add locations first in the Wind Farm Setup page."
    )
    if st.button("🏭 Go to Wind Farm Setup"):
        st.switch_page("pages/3_🏭_Wind_Farms.py")
    st.stop()

# Get available models and resolutions from backend
weather_models = api.get_weather_models()
weather_resolutions = api.get_weather_resolutions()

# Fallback defaults if API fails
if not weather_models:
    weather_models = {
        "icon_global": "ICON Global",
        "gfs_seamless": "GFS (NOAA)",
        "ecmwf_ifs04": "ECMWF IFS",
    }
if not weather_resolutions:
    weather_resolutions = [15, 30, 60]

# Create display options
model_display = {v: k for k, v in weather_models.items()}
resolution_display = {
    15: "15 min (ICON-D2)",
    30: "30 min (interpolated)",
    60: "60 min (hourly)",
}

# ==================== SETTINGS SECTION ====================
st.subheader("⚙️ Settings")

col1, col2, col3, col4 = st.columns(4)

with col1:
    loc_options = {
        f"({loc['latitude']:.2f}, {loc['longitude']:.2f})": loc for loc in locations
    }
    selected_loc_key = st.selectbox(
        "📍 Location",
        options=list(loc_options.keys()),
    )
    selected_location = loc_options[selected_loc_key]

with col2:
    available_resolutions = [r for r in weather_resolutions if r in resolution_display]
    selected_resolution_name = st.selectbox(
        "⏱️ Resolution",
        options=[resolution_display[r] for r in available_resolutions],
        index=len(available_resolutions) - 1,
    )
    resolution_minutes = next(
        r for r, name in resolution_display.items() if name == selected_resolution_name
    )

with col3:
    if resolution_minutes == 15:
        st.info("Using ICON-D2")
        selected_model = "icon_d2"
    else:
        model_names = list(model_display.keys())
        selected_model_name = st.selectbox(
            "🌐 Weather Model",
            options=model_names,
            index=0,
        )
        selected_model = model_display[selected_model_name]

with col4:
    col4a, col4b = st.columns(2)
    with col4a:
        days_past = st.number_input(
            "Historical (days)", min_value=1, max_value=90, value=7
        )
    with col4b:
        max_forecast = 2 if resolution_minutes == 15 else 16
        days_future = st.number_input(
            "Forecast (days)",
            min_value=1,
            max_value=max_forecast,
            value=min(7, max_forecast),
        )

# ==================== FETCH DATA BUTTON ====================
col_fetch, col_clear = st.columns([3, 1])

with col_fetch:
    fetch_clicked = st.button(
        "🔄 Fetch Weather Data", type="primary", use_container_width=True
    )

with col_clear:
    if st.button("🗑️ Clear", use_container_width=True):
        if "weather_data" in st.session_state:
            del st.session_state.weather_data
        st.rerun()

if fetch_clicked:
    with st.spinner("Fetching weather data from backend..."):
        weather_data = api.get_weather_data(
            latitude=selected_location["latitude"],
            longitude=selected_location["longitude"],
            model=selected_model,
            past_days=days_past,
            forecast_days=days_future,
            resolution_minutes=resolution_minutes,
        )

    if weather_data:
        hist_count = len(weather_data.get("historical", []))
        forecast_count = len(weather_data.get("forecast", []))
        st.toast(f"Fetched {hist_count} historical, {forecast_count} forecast records")

        st.session_state.weather_data = weather_data
        st.session_state.weather_location = selected_loc_key
        st.rerun()
    else:
        st.error(
            "Failed to fetch weather data. Please check your authentication and try again."
        )

st.divider()

# ==================== DISPLAY DATA (if fetched) ====================
if "weather_data" in st.session_state and st.session_state.weather_data:
    weather_data = st.session_state.weather_data

    # Convert to DataFrames
    hist_df = records_to_dataframe(weather_data.get("historical", []))
    forecast_df = records_to_dataframe(weather_data.get("forecast", []))
    model_used = weather_data.get("model_used")
    resolution_info = weather_data.get("resolution_info")

    if hist_df.empty and forecast_df.empty:
        st.error("No weather data available.")
        st.stop()

    # Show info banner
    info_parts = [
        f"📍 Location: **{st.session_state.get('weather_location', 'Unknown')}**"
    ]
    if model_used:
        info_parts.append(f"Model: **{model_used}**")
    if resolution_info:
        info_parts.append(f"Resolution: **{resolution_info}**")
    info_parts.append(f"Historical: **{len(hist_df)}** records")
    info_parts.append(f"Forecast: **{len(forecast_df)}** records")
    st.success(f"✅ {' | '.join(info_parts)}")

    # ==================== PARAMETER SELECTION ====================
    all_params = list(WEATHER_PARAMS.keys())
    display_param = st.selectbox(
        "📊 **Select Parameter to Display:**",
        options=all_params,
        format_func=lambda x: WEATHER_PARAMS[x]["label"],
        index=0,
    )

    param_config = WEATHER_PARAMS[display_param]

    # Legend
    col_legend1, col_legend2, col_legend3 = st.columns([1, 1, 2])
    with col_legend1:
        st.markdown(
            f"━━━ **Historical** <span style='color:{param_config['hist_color']}'>●</span>",
            unsafe_allow_html=True,
        )
    with col_legend2:
        st.markdown(
            f"┅┅┅ **Forecast** <span style='color:{param_config['forecast_color']}'>●</span>",
            unsafe_allow_html=True,
        )

    # ==================== COMBINED CHART ====================
    chart = render_combined_chart(
        hist_df,
        forecast_df,
        display_param,
        param_config["label"],
        hist_color=param_config["hist_color"],
        forecast_color=param_config["forecast_color"],
        y_domain=param_config.get("domain"),
    )

    if chart:
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(f"No data available for {param_config['label']}")

    # ==================== DATA TABLE ====================
    st.divider()
    st.subheader("📋 Data Table")

    data_type = st.radio(
        "Select data to display:",
        options=["Historical", "Forecast"],
        horizontal=True,
        key="data_table_type",
    )

    display_df = hist_df if data_type == "Historical" else forecast_df

    if not display_df.empty:
        # Format the dataframe for display
        display_cols = ["time"] + [c for c in display_df.columns if c != "time"]
        formatted_df = display_df[display_cols].copy()
        formatted_df["time"] = formatted_df["time"].dt.strftime("%Y-%m-%d %H:%M")

        # Use HTML table for better dark theme compatibility
        st.markdown(
            formatted_df.head(500).to_html(index=False, classes="styled-table"),
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <style>
        .styled-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
            border-radius: 8px;
            overflow: hidden;
        }
        .styled-table thead tr {
            background: #334155;
            color: #f1f5f9;
            text-align: left;
        }
        .styled-table th, .styled-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #475569;
        }
        .styled-table tbody tr {
            background: #1e293b;
            color: #e2e8f0;
        }
        .styled-table tbody tr:hover {
            background: #334155;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )
        if len(formatted_df) > 500:
            st.caption(f"Showing first 500 of {len(formatted_df)} rows")

        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            f"📥 Download {data_type} Data (CSV)",
            csv,
            file_name=f"weather_{data_type.lower()}.csv",
            mime="text/csv",
        )
    else:
        st.info(f"No {data_type.lower()} data available")

else:
    st.info("👆 Configure settings and click **Fetch Weather Data** to load data.")
