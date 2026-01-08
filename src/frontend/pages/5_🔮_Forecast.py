"""Generation Forecast page."""

import altair as alt
import pandas as pd
import streamlit as st

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.styles import inject_css

st.set_page_config(page_title="Forecast - Koppen", page_icon="⚡", layout="wide")
init_session_state()
inject_css()
render_sidebar()
require_auth()

api = get_api_client()
wind_farms = api.get_wind_farms()

if not wind_farms:
    st.warning("No wind farms found. Please create a wind farm first.")
    if st.button("Go to Wind Farm Setup", type="primary"):
        st.switch_page("pages/1_🏭_Wind_Farms.py")
    st.stop()

st.title("🔮 Generation Forecast")

farm_options = {farm["name"]: farm for farm in wind_farms}
selected_farm_name = st.selectbox(
    "🏭 Select Wind Farm", options=list(farm_options.keys())
)
selected_farm = farm_options[selected_farm_name]

st.divider()

col_gen, col_refresh = st.columns([3, 1])

with col_gen:
    st.markdown(
        "Generate power forecasts using weather data and your wind farm configuration."
    )

with col_refresh:
    if st.button("🔄 Refresh", key="refresh_forecast"):
        st.session_state.pop("forecast_data", None)
        st.rerun()

# Forecast settings
with st.expander("⚙️ Forecast Settings", expanded=False):
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        forecast_hours = st.selectbox(
            "Forecast Horizon",
            options=[24, 48, 72, 120, 168],
            index=1,
            format_func=lambda x: f"{x} hours ({x // 24} days)"
            if x >= 24
            else f"{x} hours",
        )
    with fcol2:
        forecast_granularity = st.selectbox(
            "Resolution",
            options=["min_15", "min_60"],
            index=1,
            format_func=lambda x: {"min_15": "15 minutes", "min_60": "1 hour"}.get(
                x, x
            ),
        )
    with fcol3:
        weather_model = st.selectbox(
            "Weather Model",
            options=["best_match", "gfs_seamless", "ecmwf_ifs025", "icon_seamless"],
            index=0,
            format_func=lambda x: {
                "best_match": "Best Match (Auto)",
                "gfs_seamless": "GFS (USA)",
                "ecmwf_ifs025": "ECMWF IFS (Europe)",
                "icon_seamless": "ICON (Germany)",
            }.get(x, x),
        )

if st.button("⚡ Generate New Forecast", type="primary", use_container_width=True):
    with st.spinner("Generating forecast... This may take a minute..."):
        result = api.generate_forecast(
            wind_farm_id=selected_farm["id"],
            forecast_hours=forecast_hours,
            granularity=forecast_granularity,
            weather_model=weather_model,
        )

    if result and not result.get("error") and not result.get("detail"):
        st.success(f"✅ {result.get('message', 'Forecast generated!')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Records Created", result.get("records_created", 0))
        with col2:
            total_mwh = result.get("total_forecasted_generation_kwh", 0) / 1000
            st.metric("Total Forecasted", f"{total_mwh:,.0f} MWh")
        with col3:
            st.metric("Weather Model", result.get("weather_model", "N/A"))
        st.session_state.pop("forecast_data", None)
        st.rerun()
    else:
        error_detail = (
            result.get("detail", result.get("error", "Unknown error"))
            if result
            else "Connection failed"
        )
        st.error(f"❌ Failed to generate forecast: {error_detail}")

st.divider()

# API Request Section
with st.expander("🌐 API Request for Forecasts", expanded=False):
    st.markdown("""
    Request forecast data via API. Use your authentication token to make API calls.
    """)

    # Display API Token
    col_token1, col_token2 = st.columns([3, 1])
    with col_token1:
        api_token = st.session_state.get("token", "Not logged in")
        if api_token and api_token != "Not logged in":
            st.text_input(
                "Your API Token",
                value=api_token,
                type="password",
                disabled=True,
                help="Use this token in the Authorization header: 'Bearer YOUR_TOKEN'",
                key="api_token_display",
            )
        else:
            st.warning("Please log in to get your API token")

    with col_token2:
        if st.button("🔑 Show Token", use_container_width=True):
            if api_token and api_token != "Not logged in":
                st.session_state.show_token = True
            else:
                st.error("Not logged in")

    if (
        st.session_state.get("show_token", False)
        and api_token
        and api_token != "Not logged in"
    ):
        st.info(f"**Your Token:** `{api_token}`")
        st.code(
            f"""curl -X GET "http://localhost:8000/api/v1/forecasts/request/{selected_farm["id"]}?horizon_hours=48&granularity=60min" \\
     -H "Authorization: Bearer {api_token}"

# Or using Python requests:
import requests

headers = {{"Authorization": "Bearer {api_token}"}}
response = requests.get(
    "http://localhost:8000/api/v1/forecasts/request/{selected_farm["id"]}",
    params={{'horizon_hours': 48, 'granularity': '60min'}},
    headers=headers
)
data = response.json()""",
            language="bash",
        )

    st.markdown("---")

    # API Request Form
    st.markdown("### Request Forecast via API")

    # Display generated API request
    api_token = st.session_state.get("token", "")
    base_url = "http://localhost:8000/api/v1"

    # Generate API request URL based on selected farm
    api_col1, api_col2, api_col3 = st.columns(3)

    with api_col1:
        api_horizon = st.number_input(
            "Forecast Horizon (hours)",
            min_value=1,
            max_value=168,
            value=48,
            step=1,
            help="Number of hours to forecast ahead",
            key="api_horizon",
        )

    with api_col2:
        api_start_offset = st.number_input(
            "Start Offset (hours from now)",
            min_value=0,
            max_value=168,
            value=0,
            step=1,
            help="0 = now, 24 = tomorrow",
            key="api_start_offset",
        )

    with api_col3:
        api_granularity = st.selectbox(
            "Time Resolution",
            options=["15min", "30min", "60min"],
            index=2,
            help="15-minute resolution limited to 24 hours from now",
            key="api_granularity",
        )

        # Show warning for 15-min with start offset
        if api_granularity == "15min" and api_start_offset > 0:
            max_15min_hours = 24 - api_start_offset
            if api_horizon > max_15min_hours:
                st.warning(
                    f"⚠️ 15-minute data only available for first 24 hours. With start offset of {api_start_offset}h, you'll only get ~{max_15min_hours}h of 15-min data."
                )

    # Display generated API request code
    st.markdown("#### 📋 Generated API Request Code")

    api_token = st.session_state.get("token", "YOUR_TOKEN")
    base_url = "http://localhost:8000/api/v1"
    api_url = f"{base_url}/forecasts/request/{selected_farm['id']}"
    api_params = f"horizon_hours={api_horizon}&start_hours_from_now={api_start_offset}&granularity={api_granularity}"
    full_url = f"{api_url}?{api_params}"

    # Generate code snippets
    curl_command = f"""curl -X GET "{full_url}" \\
     -H "Authorization: Bearer {api_token}" \\
     -H "Content-Type: application/json\""""

    python_code = f"""import requests

url = "{full_url}"
headers = {{
    "Authorization": "Bearer {api_token}",
    "Content-Type": "application/json"
}}

response = requests.get(url, headers=headers)
data = response.json()

# Process the forecast data
for forecast in data:
    print(f"Time: {{forecast['forecast_time']}}, Generation: {{forecast['generation']}} kW")"""

    javascript_code = f"""const url = "{full_url}";
const headers = {{
    "Authorization": "Bearer {api_token}",
    "Content-Type": "application/json"
}};

fetch(url, {{ method: 'GET', headers }})
    .then(response => response.json())
    .then(data => {{
        console.log(data);
        // Process the forecast data
        data.forEach(forecast => {{
            console.log(`Time: ${{forecast.forecast_time}}, Generation: ${{forecast.generation}} kW`);
        }});
    }})
    .catch(error => console.error('Error:', error));"""

    # Display in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["cURL", "Python", "JavaScript", "Raw URL"])

    with tab1:
        st.code(curl_command, language="bash")
        if st.button("📋 Copy cURL", key="copy_curl", use_container_width=True):
            st.info("Select and copy the code above")

    with tab2:
        st.code(python_code, language="python")
        if st.button("📋 Copy Python", key="copy_python", use_container_width=True):
            st.info("Select and copy the code above")

    with tab3:
        st.code(javascript_code, language="javascript")
        if st.button("📋 Copy JavaScript", key="copy_js", use_container_width=True):
            st.info("Select and copy the code above")

    with tab4:
        st.code(full_url, language="text")
        st.caption("Full API endpoint URL with parameters")
        if st.button("📋 Copy URL", key="copy_url", use_container_width=True):
            st.info("Select and copy the URL above")

    st.markdown("---")

    if st.button(
        "📊 Request Forecast via API", type="secondary", use_container_width=True
    ):
        with st.spinner("Requesting forecast via API..."):
            try:
                forecasts = api.request_forecast(
                    wind_farm_id=selected_farm["id"],
                    horizon_hours=api_horizon,
                    start_hours_from_now=api_start_offset,
                    granularity=api_granularity,
                )

                if forecasts:
                    # Check actual granularity and intervals
                    from datetime import datetime as dt

                    if len(forecasts) >= 2:
                        time1 = dt.fromisoformat(
                            forecasts[0]["forecast_time"].replace("Z", "+00:00")
                        )
                        time2 = dt.fromisoformat(
                            forecasts[1]["forecast_time"].replace("Z", "+00:00")
                        )
                        interval_min = (time2 - time1).total_seconds() / 60
                        actual_granularity = f"{int(interval_min)}min"

                        st.success(
                            f"✅ Retrieved {len(forecasts)} forecast records via API ({actual_granularity} intervals)"
                        )

                        # Show granularity info
                        if api_granularity == "15min" and interval_min != 15:
                            st.warning(
                                f"⚠️ Expected 15-minute intervals but got {int(interval_min)}-minute intervals. This may be due to Open-Meteo 15-minute data limitation (24 hours from now)."
                            )
                    else:
                        st.success(
                            f"✅ Retrieved {len(forecasts)} forecast records via API"
                        )

                    st.session_state["api_forecast_data"] = forecasts
                else:
                    st.warning("No forecast data available for the requested period")
                    st.session_state["api_forecast_data"] = []
            except Exception as e:
                st.error(f"Error requesting forecast: {str(e)}")
                st.session_state["api_forecast_data"] = []

    # Display API request results
    if (
        "api_forecast_data" in st.session_state
        and st.session_state["api_forecast_data"]
    ):
        st.markdown("#### API Response Data")
        api_forecasts = st.session_state["api_forecast_data"]

        # Summary metrics
        api_col1, api_col2, api_col3 = st.columns(3)
        with api_col1:
            avg_gen = (
                sum(f.get("generation", 0) for f in api_forecasts) / len(api_forecasts)
                if api_forecasts
                else 0
            )
            st.metric("Average Generation", f"{avg_gen:.2f} kW")
        with api_col2:
            max_gen = max((f.get("generation", 0) for f in api_forecasts), default=0)
            st.metric("Max Generation", f"{max_gen:.2f} kW")
        with api_col3:
            total_mwh = (
                sum(f.get("generation", 0) for f in api_forecasts) / 1000
                if api_forecasts
                else 0
            )
            st.metric("Total Forecasted", f"{total_mwh:.2f} MWh")

        # Display table
        api_table_data = []
        for f in api_forecasts[:100]:  # Show first 100
            from datetime import datetime as dt

            try:
                if isinstance(f.get("forecast_time"), str):
                    forecast_time = dt.fromisoformat(
                        f["forecast_time"].replace("Z", "+00:00")
                    )
                else:
                    forecast_time = f.get("forecast_time")
                    if hasattr(forecast_time, "strftime"):
                        pass  # Already datetime
                    else:
                        forecast_time = pd.to_datetime(forecast_time)
            except Exception:
                forecast_time = f.get("forecast_time", "N/A")

            time_str = (
                forecast_time.strftime("%Y-%m-%d %H:%M UTC")
                if hasattr(forecast_time, "strftime")
                else str(forecast_time)
            )

            api_table_data.append(
                {
                    "Time": time_str,
                    "Generation (kW)": round(f.get("generation", 0), 2)
                    if f.get("generation") is not None
                    else 0,
                    "Wind Speed (m/s)": round(f.get("wind_speed", 0), 2)
                    if f.get("wind_speed") is not None
                    else "-",
                    "Wind Direction (°)": round(f.get("wind_direction", 0), 1)
                    if f.get("wind_direction") is not None
                    else "-",
                    "Temperature (°C)": round(f.get("temperature", 0), 1)
                    if f.get("temperature") is not None
                    else "-",
                }
            )

        if api_table_data:
            api_df = pd.DataFrame(api_table_data)

            # Use HTML table for better dark theme compatibility
            st.markdown(
                api_df.to_html(index=False, escape=False, classes="styled-table"),
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

            # Download CSV
            api_csv = api_df.to_csv(index=False)
            st.download_button(
                label="📥 Download API Response CSV",
                data=api_csv,
                file_name=f"api_forecast_{selected_farm['name'].replace(' ', '_')}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            if len(api_forecasts) > 100:
                st.caption(f"Showing first 100 of {len(api_forecasts)} records")
        else:
            st.info("No data to display in table format")

st.divider()
st.markdown("### 📊 Current Forecast")

if (
    "forecast_data" not in st.session_state
    or st.session_state.get("forecast_farm_id") != selected_farm["id"]
):
    with st.spinner("Loading forecasts..."):
        forecasts = api.get_forecasts(wind_farm_id=selected_farm["id"], limit=500)
        st.session_state.forecast_data = forecasts
        st.session_state.forecast_farm_id = selected_farm["id"]

forecasts = st.session_state.get("forecast_data", [])

if not forecasts:
    st.info("📭 No forecasts available. Click 'Generate New Forecast' to create one.")
else:
    forecast_df = pd.DataFrame(forecasts)
    forecast_df["forecast_time"] = pd.to_datetime(forecast_df["forecast_time"])
    forecast_df = forecast_df.sort_values("forecast_time")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Forecast Points", len(forecast_df))
    with col2:
        if "created_at" in forecast_df.columns:
            created = pd.to_datetime(forecast_df["created_at"].iloc[0])
            st.metric("Generated", created.strftime("%Y-%m-%d %H:%M"))
    with col3:
        total_mwh = forecast_df["generation"].sum() / 1000
        st.metric("Total Forecast", f"{total_mwh:,.0f} MWh")
    with col4:
        if "weather_model" in forecast_df.columns:
            st.metric("Model", forecast_df["weather_model"].iloc[0] or "N/A")

    has_wind = (
        "wind_speed" in forecast_df.columns and forecast_df["wind_speed"].notna().any()
    )

    if has_wind:
        base = alt.Chart(forecast_df).encode(
            x=alt.X("forecast_time:T", title="Forecast Time")
        )
        gen_line = base.mark_line(strokeWidth=2, color="#9467bd").encode(
            y=alt.Y("generation:Q", title="Forecasted Generation (kW)"),
            tooltip=[
                alt.Tooltip("forecast_time:T", title="Time"),
                alt.Tooltip("generation:Q", title="Generation (kW)", format=",.0f"),
                alt.Tooltip("wind_speed:Q", title="Wind Speed (m/s)", format=".1f"),
            ],
        )
        wind_line = base.mark_line(
            strokeWidth=1.5, strokeDash=[5, 3], color="#ff7f0e"
        ).encode(
            y=alt.Y("wind_speed:Q", title="Wind Speed (m/s)"),
        )
        chart = (
            alt.layer(gen_line, wind_line)
            .resolve_scale(y="independent")
            .properties(height=400)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        chart = (
            alt.Chart(forecast_df)
            .mark_line(strokeWidth=2, color="#9467bd")
            .encode(
                x=alt.X("forecast_time:T", title="Forecast Time"),
                y=alt.Y("generation:Q", title="Forecasted Generation (kW)"),
            )
            .properties(height=400)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    with st.expander("📋 View Forecast Data"):
        cols = [
            "forecast_time",
            "generation",
            "wind_speed",
            "wind_direction",
            "temperature",
        ]
        available = [c for c in cols if c in forecast_df.columns]
        display_df = forecast_df[available].copy()
        display_df["forecast_time"] = display_df["forecast_time"].dt.strftime(
            "%Y-%m-%d %H:%M"
        )
        display_df["generation"] = pd.to_numeric(
            display_df["generation"], errors="coerce"
        ).round(1)
        if "wind_speed" in display_df.columns:
            display_df["wind_speed"] = pd.to_numeric(
                display_df["wind_speed"], errors="coerce"
            ).round(2)

        # Use HTML table for better dark theme compatibility
        st.markdown(
            display_df.to_html(index=False, classes="styled-table"),
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

        csv = display_df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            file_name=f"forecast_{selected_farm['id']}_{selected_farm['name'].replace(' ', '_')}.csv",
            mime="text/csv",
        )
