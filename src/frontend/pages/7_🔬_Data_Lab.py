"""Data Lab page - Synthetic data generation."""

import streamlit as st

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.styles import inject_css

st.set_page_config(page_title="Data Lab - Koppen", page_icon="⚡", layout="wide")
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

st.title("🔬 Data Lab")
st.caption("Generate synthetic data for testing and validation")

farm_options = {farm['name']: farm for farm in wind_farms}
selected_farm_name = st.selectbox("🏭 Select Wind Farm", options=list(farm_options.keys()))
selected_farm = farm_options[selected_farm_name]

st.divider()

# Synthetic generation section
st.subheader("🔧 Generate Synthetic Generation Data")
st.markdown("""
Generate synthetic wind generation data based on:
- Historical weather data
- Your turbine specifications and power curves
- Optional noise and random outages for realism
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**⚙️ Basic Settings**")
    days_back = st.slider("Days of Historical Data", min_value=1, max_value=365, value=30)
    granularity = st.selectbox(
        "Time Resolution",
        options=["1min", "5min", "15min", "30min", "60min"],
        index=4,
    )

with col2:
    st.markdown("**🎲 Randomness Settings**")
    add_noise = st.checkbox("Add Gaussian Noise", value=True)
    if add_noise:
        noise_std = st.slider("Noise Std Dev (%)", min_value=1.0, max_value=30.0, value=5.0)
    else:
        noise_std = 5.0

    random_outages = st.checkbox("Simulate Random Outages", value=False)
    if random_outages:
        outage_prob = st.slider("Outage Probability (per hour)", min_value=0.001, max_value=0.1, value=0.01, format="%.3f")
        outage_duration = st.slider("Avg Outage Duration (hours)", min_value=1, max_value=48, value=4)
    else:
        outage_prob = 0.01
        outage_duration = 4

st.divider()

if st.button("⚡ Generate Synthetic Data", type="primary", use_container_width=True):
    with st.spinner("Generating synthetic data... This may take a minute..."):
        result = api.generate_synthetic_data(
            wind_farm_id=selected_farm["id"],
            days_back=days_back,
            granularity=granularity,
            add_noise=add_noise,
            noise_std_percent=noise_std,
            random_outages=random_outages,
            outage_probability=outage_prob,
            outage_duration_hours=outage_duration,
        )

    if result and not result.get("error"):
        st.success(f"✅ {result['message']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Records Created", result["records_created"])
        with col2:
            total_mwh = result["total_generation_kwh"] / 1000
            st.metric("Total Generation", f"{total_mwh:,.0f} MWh")
        with col3:
            if result.get("noise_applied"):
                st.info("🎲 Noise Applied")
            if result.get("outages_simulated"):
                st.info("⚠️ Outages Simulated")

        st.session_state.pop("generation_data", None)
        st.toast("Go to 'Generation Data' page to view the generated data!")
    else:
        error_detail = result.get("detail", "Unknown error") if result else "Failed to connect"
        st.error(f"❌ Failed to generate data: {error_detail}")

# Historical Forecast Section
st.divider()
st.subheader("🔮 Generate Historical Forecasts")
st.markdown("""
Generate "forecasts" for past dates using historical weather data.
This allows you to compare forecast accuracy against actual/synthetic data.
""")

hcol1, hcol2 = st.columns(2)

with hcol1:
    hist_forecast_days = st.slider(
        "Days Back for Historical Forecast",
        min_value=1,
        max_value=90,
        value=30,
        key="hist_forecast_days",
    )

with hcol2:
    hist_granularity = st.selectbox(
        "Resolution",
        options=["min_15", "min_60"],
        index=1,
        format_func=lambda x: {"min_15": "15 minutes", "min_60": "1 hour"}.get(x, x),
        key="hist_forecast_granularity",
    )

if st.button("⚡ Generate Historical Forecast", type="primary", use_container_width=True):
    with st.spinner("Generating historical forecasts... This may take a minute..."):
        result = api.generate_historical_forecast(
            wind_farm_id=selected_farm["id"],
            days_back=hist_forecast_days,
            granularity=hist_granularity,
        )

    if result and not result.get("error") and not result.get("detail"):
        st.success(f"✅ {result.get('message', 'Historical forecast generated!')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Records Created", result.get("records_created", 0))
        with col2:
            total_mwh = result.get("total_forecasted_generation_kwh", 0) / 1000
            st.metric("Total Forecasted", f"{total_mwh:,.0f} MWh")
        with col3:
            st.metric("Period", f"{hist_forecast_days} days back")

        st.session_state.pop("forecast_data", None)
        st.toast("Go to 'Analysis' page to compare with actual data!")
    else:
        error_detail = result.get("detail", result.get("error", "Unknown error")) if result else "Connection failed"
        st.error(f"❌ Failed to generate historical forecast: {error_detail}")

