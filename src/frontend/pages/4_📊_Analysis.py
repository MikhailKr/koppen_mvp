"""Compare & Metrics page."""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.styles import inject_css

st.set_page_config(page_title="Analysis - Koppen", page_icon="⚡", layout="wide")
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

st.title("📊 Compare & Metrics")

farm_options = {farm['name']: farm for farm in wind_farms}
selected_farm_name = st.selectbox("🏭 Select Wind Farm", options=list(farm_options.keys()))
selected_farm = farm_options[selected_farm_name]

st.divider()

st.markdown("Select a forecast to compare with actual generation data.")

with st.spinner("Loading available forecasts..."):
    all_forecasts = api.get_forecasts(wind_farm_id=selected_farm["id"], limit=10000)

if not all_forecasts:
    st.info("📭 No forecasts available for this wind farm. Generate forecasts first.")
    if st.button("Go to Forecast Page"):
        st.switch_page("pages/4_🔮_Forecast.py")
    st.stop()

all_forecast_df = pd.DataFrame(all_forecasts)
all_forecast_df["created_at"] = pd.to_datetime(all_forecast_df["created_at"])
all_forecast_df["forecast_time"] = pd.to_datetime(all_forecast_df["forecast_time"])
all_forecast_df["batch_id"] = all_forecast_df["created_at"].dt.floor("min")

forecast_batches = (
    all_forecast_df.groupby("batch_id")
    .agg(
        records=("id", "count"),
        start_time=("forecast_time", "min"),
        end_time=("forecast_time", "max"),
        weather_model=("weather_model", "first"),
        total_gen=("generation", "sum"),
    )
    .reset_index()
    .sort_values("batch_id", ascending=False)
)

batch_options = {}
for _, row in forecast_batches.iterrows():
    batch_key = row["batch_id"]
    label = (
        f"{row['batch_id'].strftime('%Y-%m-%d %H:%M')} | "
        f"{row['start_time'].strftime('%m/%d')} → {row['end_time'].strftime('%m/%d')} | "
        f"{row['records']} pts | {row['weather_model'] or 'N/A'}"
    )
    batch_options[label] = batch_key

selected_batch_label = st.selectbox(
    "🔮 Select Forecast to Compare",
    options=list(batch_options.keys()),
    help="Forecasts are grouped by creation date.",
)
selected_batch = batch_options[selected_batch_label]

selected_forecast_df = all_forecast_df[all_forecast_df["batch_id"] == selected_batch].copy()
forecast_start = selected_forecast_df["forecast_time"].min()
forecast_end = selected_forecast_df["forecast_time"].max()

col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.metric("Forecast Period", f"{forecast_start.strftime('%Y-%m-%d')} → {forecast_end.strftime('%Y-%m-%d')}")
with col_info2:
    st.metric("Forecast Points", len(selected_forecast_df))
with col_info3:
    model = selected_forecast_df["weather_model"].iloc[0] if "weather_model" in selected_forecast_df.columns else "N/A"
    st.metric("Weather Model", model or "N/A")

st.divider()

if st.button("🔄 Load & Compare", type="primary", use_container_width=True):
    with st.spinner("Loading actual generation data..."):
        actual_data = api.get_farm_generation_records(
            wind_farm_id=selected_farm["id"],
            start_time=forecast_start.isoformat(),
            end_time=forecast_end.isoformat(),
            limit=10000,
        )
        st.session_state.compare_actual = actual_data
        st.session_state.compare_forecast = selected_forecast_df.to_dict("records")
        st.session_state.compare_batch_id = str(selected_batch)

actual_data = st.session_state.get("compare_actual", [])
if st.session_state.get("compare_batch_id") == str(selected_batch):
    forecast_data = st.session_state.get("compare_forecast", [])
else:
    forecast_data = []

if actual_data or forecast_data:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Actual Records", len(actual_data))
    with col2:
        st.metric("Forecast Records", len(forecast_data))

if actual_data and forecast_data:
    actual_df = pd.DataFrame(actual_data)
    forecast_df = pd.DataFrame(forecast_data)

    if "timestamp" in actual_df.columns:
        actual_df["time"] = pd.to_datetime(actual_df["timestamp"], utc=True)
    if "forecast_time" in forecast_df.columns:
        forecast_df["time"] = pd.to_datetime(forecast_df["forecast_time"], utc=True)

    actual_df = actual_df.rename(columns={"generation": "actual_generation"})
    forecast_df = forecast_df.rename(columns={"generation": "forecast_generation"})

    actual_df["time_hour"] = actual_df["time"].dt.floor("h")
    forecast_df["time_hour"] = forecast_df["time"].dt.floor("h")

    actual_hourly = actual_df.groupby("time_hour").agg({"actual_generation": "mean"}).reset_index()
    forecast_hourly = forecast_df.groupby("time_hour").agg({"forecast_generation": "mean"}).reset_index()

    merged_df = pd.merge(actual_hourly, forecast_hourly, on="time_hour", how="inner")

    if len(merged_df) > 0:
        st.success(f"✅ Found {len(merged_df)} overlapping time points for comparison")

        actual_vals = merged_df["actual_generation"].values
        forecast_vals = merged_df["forecast_generation"].values

        mae = float(np.mean(np.abs(actual_vals - forecast_vals)))
        rmse = float(np.sqrt(np.mean((actual_vals - forecast_vals) ** 2)))

        mask = actual_vals > 0
        mape = float(np.mean(np.abs((actual_vals[mask] - forecast_vals[mask]) / actual_vals[mask])) * 100) if mask.sum() > 0 else 0.0
        bias = float(np.mean(forecast_vals - actual_vals))

        st.markdown("### 📈 Accuracy Metrics")
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.metric("MAE", f"{mae:,.1f} kW", help="Mean Absolute Error")
        with mcol2:
            st.metric("RMSE", f"{rmse:,.1f} kW", help="Root Mean Square Error")
        with mcol3:
            st.metric("MAPE", f"{mape:.1f}%", help="Mean Absolute Percentage Error")
        with mcol4:
            bias_direction = "↑ Over" if bias > 0 else "↓ Under"
            st.metric("Bias", f"{abs(bias):,.1f} kW", delta=bias_direction)

        st.markdown("### 📊 Summary Statistics")
        scol1, scol2, scol3, scol4 = st.columns(4)
        with scol1:
            st.metric("Avg Actual", f"{np.mean(actual_vals):,.0f} kW")
        with scol2:
            st.metric("Avg Forecast", f"{np.mean(forecast_vals):,.0f} kW")
        with scol3:
            st.metric("Total Actual", f"{np.sum(actual_vals) / 1000:,.0f} MWh")
        with scol4:
            st.metric("Total Forecast", f"{np.sum(forecast_vals) / 1000:,.0f} MWh")

        st.divider()
        st.markdown("### 📉 Actual vs Forecast Comparison")

        chart_df = merged_df.rename(columns={"time_hour": "Time"})
        chart_melted = chart_df.melt(
            id_vars=["Time"],
            value_vars=["actual_generation", "forecast_generation"],
            var_name="Type",
            value_name="Generation (kW)",
        )
        chart_melted["Type"] = chart_melted["Type"].map({
            "actual_generation": "Actual",
            "forecast_generation": "Forecast",
        })

        comparison_chart = alt.Chart(chart_melted).mark_line(strokeWidth=2).encode(
            x=alt.X("Time:T", title="Time"),
            y=alt.Y("Generation (kW):Q", title="Generation (kW)"),
            color=alt.Color("Type:N", scale=alt.Scale(domain=["Actual", "Forecast"], range=["#2ecc71", "#9b59b6"])),
            strokeDash=alt.condition(alt.datum.Type == "Forecast", alt.value([5, 3]), alt.value([0])),
        ).properties(height=400).interactive()

        st.altair_chart(comparison_chart, use_container_width=True)

        st.markdown("### 📊 Error Distribution")
        merged_df["error"] = merged_df["forecast_generation"] - merged_df["actual_generation"]

        error_chart = alt.Chart(merged_df).mark_bar(opacity=0.7).encode(
            x=alt.X("error:Q", bin=alt.Bin(maxbins=30), title="Forecast Error (kW)"),
            y=alt.Y("count()", title="Frequency"),
            color=alt.condition(alt.datum.error > 0, alt.value("#e74c3c"), alt.value("#3498db")),
        ).properties(height=250)

        st.altair_chart(error_chart, use_container_width=True)

        with st.expander("📋 View Comparison Data"):
            display_merged = merged_df[["time_hour", "actual_generation", "forecast_generation", "error"]].copy()
            display_merged.columns = ["Time", "Actual (kW)", "Forecast (kW)", "Error (kW)"]
            display_merged["Time"] = display_merged["Time"].dt.strftime("%Y-%m-%d %H:%M")
            
            # Use HTML table for better dark theme compatibility
            st.markdown(
                display_merged.to_html(index=False, classes="styled-table"),
                unsafe_allow_html=True,
            )
            st.markdown("""
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
            """, unsafe_allow_html=True)

            csv = display_merged.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, file_name=f"comparison_{selected_farm['id']}.csv", mime="text/csv")
    else:
        st.warning("⚠️ No overlapping time points found between actual and forecast data.")

elif actual_data and not forecast_data:
    st.info("📭 Click 'Load & Compare' to fetch data for this forecast period.")
elif forecast_data and not actual_data:
    st.warning("📭 No actual generation data found. Generate synthetic data first in Data Lab.")
else:
    st.info("👆 Click 'Load & Compare' to compare the selected forecast with actual data.")
