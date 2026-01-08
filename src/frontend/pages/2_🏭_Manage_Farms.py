"""Manage Wind Farms - View and manage existing farms."""

import pandas as pd
import pydeck as pdk
import streamlit as st

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.styles import inject_css

st.set_page_config(page_title="Manage Farms - Koppen", page_icon="⚡", layout="wide")
init_session_state()
inject_css()
render_sidebar()
require_auth()

api = get_api_client()

st.title("🏭 Manage Wind Farms")

# Action buttons
col1, col2, _ = st.columns([1, 1, 2])
with col1:
    if st.button("➕ Create New Farm", use_container_width=True, type="primary"):
        st.switch_page("pages/1_➕_Create_Farm.py")

# Load farms
with st.spinner("Loading..."):
    farms = api.get_wind_farms()

if not farms:
    st.info("No wind farms yet. Create your first one!")
    if st.button("➕ Create Wind Farm", type="primary"):
        st.switch_page("pages/1_➕_Create_Farm.py")
    st.stop()

st.divider()

# Display farms
for farm in farms:
    fleets = api.get_fleets(wind_farm_id=farm["id"])
    total_turbines = sum(f["number_of_turbines"] for f in fleets)
    total_capacity = sum(
        f["number_of_turbines"]
        * (f.get("wind_turbine", {}).get("nominal_power", 0) or 0)
        for f in fleets
    )

    with st.container(border=True):
        # Header row
        col_info, col_stats, col_actions = st.columns([2, 2, 1])

        with col_info:
            st.markdown(f"### 🏭 {farm['name']}")
            st.markdown(f"*{farm.get('description') or 'No description'}*")
            st.caption(
                f"ID: {farm['id']} | Created: {farm.get('created_at', 'N/A')[:10]}"
            )

        with col_stats:
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            with stat_col1:
                st.metric("Turbines", total_turbines)
            with stat_col2:
                st.metric("Capacity", f"{total_capacity:.1f} MW")
            with stat_col3:
                locations = len(
                    {
                        f.get("location", {}).get("id")
                        for f in fleets
                        if f.get("location")
                    }
                )
                st.metric("Locations", locations)

        with col_actions:
            if st.button(
                "🗑️ Delete", key=f"del_farm_{farm['id']}", use_container_width=True
            ):
                with st.spinner("Deleting..."):
                    # First delete all fleets associated with this farm
                    for fleet in fleets:
                        api.delete_fleet(fleet["id"])
                    # Then delete the farm
                    result = api.delete_wind_farm(farm["id"])
                    if result.get("success"):
                        st.success("Deleted!")
                        st.rerun()
                    else:
                        error_msg = result.get("error", "Unknown error")
                        st.error(f"Failed to delete: {error_msg}")

        # Expandable details
        with st.expander("📋 View Details", expanded=False):
            if fleets:
                st.markdown("**Turbine Fleets:**")
                for fleet in fleets:
                    turb = fleet.get("wind_turbine") or {}
                    loc = fleet.get("location") or {}

                    fleet_col1, fleet_col2, fleet_col3 = st.columns([2, 2, 1])
                    with fleet_col1:
                        st.markdown(
                            f"⚡ **{fleet['number_of_turbines']}x** {turb.get('turbine_type', 'Unknown')}"
                        )
                        st.caption(
                            f"Power: {turb.get('nominal_power', 0)} MW | Hub: {turb.get('hub_height', 0)} m"
                        )
                    with fleet_col2:
                        st.markdown(
                            f"📍 ({loc.get('latitude', 0):.4f}, {loc.get('longitude', 0):.4f})"
                        )
                    with fleet_col3:
                        if st.button(
                            "❌", key=f"del_fleet_{fleet['id']}"
                        ) and api.delete_fleet(fleet["id"]):
                            st.rerun()

                st.divider()

                # Map of fleet locations with custom markers
                if any(f.get("location") for f in fleets):
                    st.markdown("**📍 Farm Locations:**")
                    map_data = pd.DataFrame(
                        [
                            {
                                "lat": f["location"]["latitude"],
                                "lon": f["location"]["longitude"],
                                "turbines": f["number_of_turbines"],
                                "name": f.get("wind_turbine", {}).get(
                                    "turbine_type", "Turbine"
                                ),
                            }
                            for f in fleets
                            if f.get("location")
                        ]
                    )

                    # Calculate center
                    center_lat = map_data["lat"].mean()
                    center_lon = map_data["lon"].mean()

                    # Create pydeck layer with larger icons
                    layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=map_data,
                        get_position=["lon", "lat"],
                        get_radius=50000,  # Radius in meters
                        get_fill_color=[14, 165, 233, 200],  # Blue with transparency
                        pickable=True,
                        auto_highlight=True,
                    )

                    # Icon layer for wind turbine symbol
                    icon_layer = pdk.Layer(
                        "TextLayer",
                        data=map_data,
                        get_position=["lon", "lat"],
                        get_text="'🏭'",
                        get_size=24,
                        get_color=[255, 255, 255],
                        get_angle=0,
                        get_text_anchor="'middle'",
                        get_alignment_baseline="'center'",
                    )

                    view_state = pdk.ViewState(
                        latitude=center_lat,
                        longitude=center_lon,
                        zoom=5,
                        pitch=0,
                    )

                    st.pydeck_chart(
                        pdk.Deck(
                            layers=[layer, icon_layer],
                            initial_view_state=view_state,
                            tooltip={"text": "{name}\n{turbines} turbines"},
                            map_style="mapbox://styles/mapbox/dark-v10",
                        )
                    )
            else:
                st.info("No turbines assigned to this farm yet.")
                if st.button("➕ Add Turbines", key=f"add_turb_{farm['id']}"):
                    st.session_state.wizard_farm = farm
                    st.session_state.wizard_step = 2
                    st.switch_page("pages/1_➕_Create_Farm.py")

st.divider()

# Quick stats
st.markdown("### 📊 Portfolio Summary")

total_farms = len(farms)
total_all_turbines = sum(
    sum(f["number_of_turbines"] for f in api.get_fleets(wind_farm_id=farm["id"]))
    for farm in farms
)
total_all_capacity = sum(
    sum(
        f["number_of_turbines"]
        * (f.get("wind_turbine", {}).get("nominal_power", 0) or 0)
        for f in api.get_fleets(wind_farm_id=farm["id"])
    )
    for farm in farms
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Farms", total_farms)
with col2:
    st.metric("Total Turbines", total_all_turbines)
with col3:
    st.metric("Total Capacity", f"{total_all_capacity:.1f} MW")
