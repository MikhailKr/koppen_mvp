"""Generation Data page."""

from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.styles import inject_css

st.set_page_config(page_title="Generation Data - Koppen", page_icon="⚡", layout="wide")
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

st.title("📈 Generation Data")

farm_options = {farm["name"]: farm for farm in wind_farms}
selected_farm_name = st.selectbox(
    "🏭 Select Wind Farm", options=list(farm_options.keys())
)
selected_farm = farm_options[selected_farm_name]

st.divider()

# Date range selection
col_date1, col_date2, col_refresh = st.columns([2, 2, 1])

default_end = datetime.now()
default_start = default_end - timedelta(days=30)

with col_date1:
    start_date = st.date_input(
        "Start Date", value=default_start.date(), key="gen_start_date"
    )
with col_date2:
    end_date = st.date_input("End Date", value=default_end.date(), key="gen_end_date")
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh_clicked = st.button("🔄 Refresh", use_container_width=True)

cache_key = f"{selected_farm['id']}_{start_date}_{end_date}"

if refresh_clicked or st.session_state.get("generation_cache_key") != cache_key:
    with st.spinner("Loading generation records..."):
        start_time_str = datetime.combine(start_date, datetime.min.time()).isoformat()
        end_time_str = datetime.combine(end_date, datetime.max.time()).isoformat()
        records = api.get_farm_generation_records(
            wind_farm_id=selected_farm["id"],
            start_time=start_time_str,
            end_time=end_time_str,
            limit=10000,
        )
        st.session_state.generation_data = records
        st.session_state.generation_cache_key = cache_key

records = st.session_state.get("generation_data", [])

if not records:
    st.info("📭 No generation data found for this wind farm.")
    st.markdown("**Options:**")
    st.markdown("- Go to the **Data Lab** page to generate synthetic data")
    st.markdown("- Or upload real generation data via the API")
else:
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", len(df))
    with col2:
        synthetic_count = (
            df["is_synthetic"].sum() if "is_synthetic" in df.columns else 0
        )
        st.metric("Synthetic", synthetic_count)
    with col3:
        real_count = len(df) - synthetic_count
        st.metric("Real", real_count)
    with col4:
        total_gen = df["generation"].sum() / 1000
        st.metric("Total Generation", f"{total_gen:,.0f} MWh")

    st.markdown("### 📊 Generation & Wind Speed Over Time")

    if "is_synthetic" in df.columns:
        df["data_type"] = df["is_synthetic"].apply(
            lambda x: "Synthetic" if x else "Real"
        )
    else:
        df["data_type"] = "Unknown"

    has_wind_speed = "wind_speed" in df.columns and df["wind_speed"].notna().any()

    if has_wind_speed:
        base = alt.Chart(df).encode(x=alt.X("timestamp:T", title="Time"))
        generation_line = base.mark_line(strokeWidth=2, color="#1f77b4").encode(
            y=alt.Y(
                "generation:Q",
                title="Generation (kW)",
                axis=alt.Axis(titleColor="#1f77b4"),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time"),
                alt.Tooltip("generation:Q", title="Generation (kW)", format=",.1f"),
                alt.Tooltip("wind_speed:Q", title="Wind Speed (m/s)", format=".1f"),
                alt.Tooltip("data_type:N", title="Type"),
            ],
        )
        wind_line = base.mark_line(
            strokeWidth=1.5, strokeDash=[5, 3], color="#ff7f0e"
        ).encode(
            y=alt.Y(
                "wind_speed:Q",
                title="Wind Speed (m/s)",
                axis=alt.Axis(titleColor="#ff7f0e"),
            ),
        )
        chart = (
            alt.layer(generation_line, wind_line)
            .resolve_scale(y="independent")
            .properties(height=450)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        chart = (
            alt.Chart(df)
            .mark_line(strokeWidth=1.5)
            .encode(
                x=alt.X("timestamp:T", title="Time"),
                y=alt.Y("generation:Q", title="Generation (kW)"),
                color=alt.Color(
                    "data_type:N",
                    title="Data Type",
                    scale=alt.Scale(
                        domain=["Real", "Synthetic"], range=["#2ca02c", "#1f77b4"]
                    ),
                ),
            )
            .properties(height=400)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    with st.expander("📋 View Data Table"):
        cols = [
            "timestamp",
            "generation",
            "wind_speed",
            "wind_direction",
            "temperature",
            "granularity",
            "is_synthetic",
        ]
        available_cols = [c for c in cols if c in df.columns]
        display_df = df[available_cols].copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        display_df["generation"] = pd.to_numeric(
            display_df["generation"], errors="coerce"
        ).round(2)
        if "wind_speed" in display_df.columns:
            display_df["wind_speed"] = pd.to_numeric(
                display_df["wind_speed"], errors="coerce"
            ).round(2)

        # Use HTML table for better dark theme compatibility
        st.markdown(
            display_df.head(500).to_html(index=False, classes="styled-table"),
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
        if len(display_df) > 500:
            st.caption(f"Showing first 500 of {len(display_df)} rows")

        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            file_name=f"generation_{selected_farm['id']}.csv",
            mime="text/csv",
        )
