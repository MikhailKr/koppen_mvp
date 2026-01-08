"""Create Wind Farm - Step-by-step wizard."""

import pandas as pd
import streamlit as st

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.config import PREDEFINED_LOCATIONS
from frontend.styles import inject_css

st.set_page_config(
    page_title="Create Wind Farm - Koppen", page_icon="⚡", layout="wide"
)
init_session_state()
inject_css()
render_sidebar()
require_auth()

api = get_api_client()

# Initialize wizard state
if "wizard_step" not in st.session_state:
    st.session_state.wizard_step = 1
if "wizard_farm" not in st.session_state:
    st.session_state.wizard_farm = None
if "wizard_fleets" not in st.session_state:
    st.session_state.wizard_fleets = []

st.title("➕ Create Wind Farm")

# Progress indicator using Streamlit columns
current_step = st.session_state.wizard_step
steps = ["Farm Details", "Add Turbines", "Review & Finish"]

col1, col2, col3 = st.columns(3)
for i, (col, step) in enumerate(zip([col1, col2, col3], steps, strict=False), 1):
    with col:
        if i < current_step:
            st.markdown(f"### ✅ {step}")
            st.caption("Completed")
        elif i == current_step:
            st.markdown(f"### 🔵 {step}")
            st.caption("Current step")
        else:
            st.markdown(f"### ⚪ {step}")
            st.caption("Pending")

st.divider()

# ==================== STEP 1: Farm Details ====================
if current_step == 1:
    st.subheader("🏭 Create Your Wind Farm")

    with st.form("farm_form"):
        farm_name = st.text_input(
            "Farm Name *", placeholder="e.g., North Sea Wind Park"
        )
        farm_desc = st.text_area("Description", placeholder="Optional description...")

        col1, col2 = st.columns(2)
        with col2:
            submitted = st.form_submit_button(
                "Next →", use_container_width=True, type="primary"
            )

        if submitted:
            if not farm_name:
                st.error("Farm name is required")
            else:
                result = api.create_wind_farm(farm_name, farm_desc or None)
                if result and not result.get("error"):
                    st.session_state.wizard_farm = result
                    st.session_state.wizard_step = 2
                    st.rerun()
                else:
                    st.error("Failed to create wind farm")

# ==================== STEP 2: Add Turbines ====================
elif current_step == 2:
    farm = st.session_state.wizard_farm
    st.subheader(f"⚡ Add Turbines to '{farm['name']}'")

    # Load existing data
    all_turbines = api.get_wind_turbines()
    all_locations = api.get_locations()
    all_curves = api.get_power_curves()

    # Show current fleets
    current_fleets = api.get_fleets(wind_farm_id=farm["id"])
    if current_fleets:
        st.markdown("**Added Turbine Fleets:**")
        for fleet in current_fleets:
            turb = fleet.get("wind_turbine") or {}
            loc = fleet.get("location") or {}
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown(
                        f"**{fleet['number_of_turbines']}x {turb.get('turbine_type', 'Unknown')}**"
                    )
                    st.caption(f"{turb.get('nominal_power', 0)} MW each")
                with col2:
                    st.markdown(
                        f"📍 ({loc.get('latitude', 0):.2f}, {loc.get('longitude', 0):.2f})"
                    )
                with col3:
                    if st.button("❌", key=f"rm_fleet_{fleet['id']}"):
                        api.delete_fleet(fleet["id"])
                        st.rerun()
        st.divider()

    # Add new fleet section
    st.markdown("### ➕ Add Turbine Fleet")

    tab_existing, tab_new = st.tabs(["Use Existing Turbine", "Create New Turbine"])

    with tab_existing:
        if not all_turbines:
            st.info(
                "No turbine specs available. Create one in the 'Create New Turbine' tab."
            )
        else:
            turb_opts = {
                f"{t.get('turbine_type', 'Unknown')} ({t['nominal_power']}MW)": t["id"]
                for t in all_turbines
            }
            selected_turb = st.selectbox(
                "Select Turbine", list(turb_opts.keys()), key="existing_turb"
            )
            selected_turb_id = turb_opts[selected_turb] if selected_turb else None

            st.session_state.selected_turbine_id = selected_turb_id

    with tab_new:
        st.markdown("**Create New Turbine Specification:**")

        new_turb_type = st.text_input(
            "Turbine Model", placeholder="e.g., Vestas V150", key="new_turb_type"
        )
        col1, col2 = st.columns(2)
        with col1:
            new_hub_height = st.number_input(
                "Hub Height (m)",
                value=100.0,
                min_value=10.0,
                max_value=300.0,
                key="new_hub",
            )
        with col2:
            new_nominal_power = st.number_input(
                "Nominal Power (MW)",
                value=4.0,
                min_value=0.1,
                max_value=20.0,
                key="new_power",
            )

        # Power curve selection or creation
        st.markdown("**Power Curve:**")
        curve_choice = st.radio(
            "", ["Use Existing", "Create New"], horizontal=True, key="curve_choice"
        )

        new_curve_id = None
        default_curve = None

        if curve_choice == "Use Existing":
            if all_curves:
                curve_opts = {}
                for c in all_curves:
                    curve_name = c.get("name") or f"Curve #{c['id']}"
                    curve_opts[curve_name] = c["id"]
                selected_curve = st.selectbox(
                    "Select Power Curve", list(curve_opts.keys()), key="existing_curve"
                )
                new_curve_id = curve_opts[selected_curve]

                # Show selected curve preview
                selected_curve_data = next(
                    (c for c in all_curves if c["id"] == new_curve_id), None
                )
                if selected_curve_data and selected_curve_data.get(
                    "wind_speed_value_map"
                ):
                    wsvm = selected_curve_data["wind_speed_value_map"]
                    chart_data = pd.DataFrame(
                        [
                            {"Wind Speed (m/s)": float(k), "Power (kW)": v}
                            for k, v in sorted(wsvm.items(), key=lambda x: float(x[0]))
                        ]
                    )
                    st.line_chart(
                        chart_data, x="Wind Speed (m/s)", y="Power (kW)", height=200
                    )
            else:
                st.info("No power curves available. Select 'Create New' above.")
        else:
            # Power curve creation options
            curve_method = st.radio(
                "Creation method:",
                ["Auto-generate (scaled)", "Manual entry (by points)"],
                horizontal=True,
                key="curve_method",
            )

            if curve_method == "Auto-generate (scaled)":
                st.markdown("**Auto-generated curve scaled to your turbine:**")

                # Default 1MW curve scaled to nominal power (values in kW)
                default_curve = {
                    "0": 0,
                    "3": int(50 * new_nominal_power),
                    "4": int(100 * new_nominal_power),
                    "5": int(150 * new_nominal_power),
                    "6": int(250 * new_nominal_power),
                    "7": int(350 * new_nominal_power),
                    "8": int(500 * new_nominal_power),
                    "9": int(650 * new_nominal_power),
                    "10": int(800 * new_nominal_power),
                    "11": int(900 * new_nominal_power),
                    "12": int(950 * new_nominal_power),
                    "13": int(980 * new_nominal_power),
                    "14": int(1000 * new_nominal_power),
                    "15": int(1000 * new_nominal_power),
                    "20": int(1000 * new_nominal_power),
                    "25": 0,
                }

                # Show curve preview
                chart_data = pd.DataFrame(
                    [
                        {"Wind Speed (m/s)": float(k), "Power (kW)": v}
                        for k, v in sorted(
                            default_curve.items(), key=lambda x: float(x[0])
                        )
                    ]
                )
                st.line_chart(
                    chart_data, x="Wind Speed (m/s)", y="Power (kW)", height=200
                )

                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.metric("Max Power", f"{int(1000 * new_nominal_power)} kW")
                with col_stats2:
                    st.metric("Cut-in", "3 m/s")
                with col_stats3:
                    st.metric("Cut-out", "25 m/s")

            else:
                st.markdown("**Enter power curve points manually:**")

                # Initialize manual curve points in session state with 25 points
                if (
                    "manual_curve_points" not in st.session_state
                    or len(st.session_state.manual_curve_points) < 10
                ):
                    # Typical power curve with 25 points
                    nominal_kw = int(1000 * new_nominal_power)
                    st.session_state.manual_curve_points = [
                        {"wind_speed": 0, "power": 0},
                        {"wind_speed": 1, "power": 0},
                        {"wind_speed": 2, "power": 0},
                        {"wind_speed": 3, "power": int(0.02 * nominal_kw)},
                        {"wind_speed": 4, "power": int(0.05 * nominal_kw)},
                        {"wind_speed": 5, "power": int(0.10 * nominal_kw)},
                        {"wind_speed": 6, "power": int(0.18 * nominal_kw)},
                        {"wind_speed": 7, "power": int(0.28 * nominal_kw)},
                        {"wind_speed": 8, "power": int(0.40 * nominal_kw)},
                        {"wind_speed": 9, "power": int(0.54 * nominal_kw)},
                        {"wind_speed": 10, "power": int(0.68 * nominal_kw)},
                        {"wind_speed": 11, "power": int(0.80 * nominal_kw)},
                        {"wind_speed": 12, "power": int(0.90 * nominal_kw)},
                        {"wind_speed": 13, "power": int(0.96 * nominal_kw)},
                        {"wind_speed": 14, "power": int(0.99 * nominal_kw)},
                        {"wind_speed": 15, "power": nominal_kw},
                        {"wind_speed": 16, "power": nominal_kw},
                        {"wind_speed": 17, "power": nominal_kw},
                        {"wind_speed": 18, "power": nominal_kw},
                        {"wind_speed": 19, "power": nominal_kw},
                        {"wind_speed": 20, "power": nominal_kw},
                        {"wind_speed": 21, "power": nominal_kw},
                        {"wind_speed": 22, "power": nominal_kw},
                        {"wind_speed": 23, "power": nominal_kw},
                        {"wind_speed": 24, "power": nominal_kw},
                        {"wind_speed": 25, "power": 0},
                    ]

                # Sort points by wind speed
                st.session_state.manual_curve_points.sort(key=lambda x: x["wind_speed"])

                # Action buttons row
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
                with btn_col1:
                    if st.button(
                        "🔄 Sort & Refresh",
                        key="sort_points",
                        use_container_width=True,
                        type="primary",
                    ):
                        st.session_state.manual_curve_points.sort(
                            key=lambda x: x["wind_speed"]
                        )
                        st.rerun()
                with btn_col2:
                    st.markdown(
                        f"**{len(st.session_state.manual_curve_points)} points**"
                    )

                st.caption("📜 Edit values, then click 'Sort & Refresh' to reorder.")

                # Display as HTML table for proper dark theme rendering
                table_html = '<div style="max-height: 300px; overflow-y: auto; border: 2px solid #0ea5e9; border-radius: 8px; margin: 0.5rem 0;">'
                table_html += '<table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">'
                table_html += '<thead><tr style="background: #334155; color: #f1f5f9; position: sticky; top: 0;">'
                table_html += '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #475569;">#</th>'
                table_html += '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #475569;">Wind (m/s)</th>'
                table_html += '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #475569;">Power (kW)</th>'
                table_html += "</tr></thead><tbody>"

                for i, p in enumerate(st.session_state.manual_curve_points):
                    table_html += '<tr style="background: #1e293b; color: #e2e8f0;">'
                    table_html += f'<td style="padding: 6px; text-align: center; border-bottom: 1px solid #475569;">{i + 1}</td>'
                    table_html += f'<td style="padding: 6px; text-align: center; border-bottom: 1px solid #475569;">{p["wind_speed"]:.1f}</td>'
                    table_html += f'<td style="padding: 6px; text-align: center; border-bottom: 1px solid #475569;">{int(p["power"]):,}</td>'
                    table_html += "</tr>"

                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)

                # Add new point section
                st.markdown("**➕ Add New Point:**")
                add_cols = st.columns([2, 2, 1])
                with add_cols[0]:
                    add_ws = st.number_input(
                        "Wind Speed (m/s)",
                        value=0.0,
                        min_value=0.0,
                        max_value=50.0,
                        step=0.5,
                        key="add_ws",
                    )
                with add_cols[1]:
                    add_pwr = st.number_input(
                        "Power (kW)",
                        value=0,
                        min_value=0,
                        max_value=50000,
                        step=10,
                        key="add_pwr",
                    )
                with add_cols[2]:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("➕ Add", key="add_point", type="primary"):
                        st.session_state.manual_curve_points.append(
                            {"wind_speed": add_ws, "power": add_pwr}
                        )
                        st.session_state.manual_curve_points.sort(
                            key=lambda x: x["wind_speed"]
                        )
                        st.rerun()

                # Edit section
                st.markdown("**✏️ Edit Point:**")
                edit_cols = st.columns([1, 2, 2, 1])
                with edit_cols[0]:
                    edit_idx = st.number_input(
                        "Point #",
                        min_value=1,
                        max_value=len(st.session_state.manual_curve_points),
                        value=1,
                        key="edit_idx",
                    )
                with edit_cols[1]:
                    current_point = st.session_state.manual_curve_points[edit_idx - 1]
                    new_ws = st.number_input(
                        "Wind Speed",
                        value=float(current_point["wind_speed"]),
                        min_value=0.0,
                        max_value=50.0,
                        step=0.5,
                        key="edit_ws",
                    )
                with edit_cols[2]:
                    new_pwr = st.number_input(
                        "Power (kW)",
                        value=int(current_point["power"]),
                        min_value=0,
                        max_value=50000,
                        step=10,
                        key="edit_pwr",
                    )
                with edit_cols[3]:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("✏️ Update", key="update_point"):
                        st.session_state.manual_curve_points[edit_idx - 1] = {
                            "wind_speed": new_ws,
                            "power": new_pwr,
                        }
                        st.rerun()

                # Delete section
                del_cols = st.columns([1, 2, 1])
                with del_cols[0]:
                    del_idx = st.number_input(
                        "Delete #",
                        min_value=1,
                        max_value=len(st.session_state.manual_curve_points),
                        value=1,
                        key="del_idx",
                    )
                  with del_cols[1]:
                      if len(st.session_state.manual_curve_points) > 3 and st.button("🗑️ Delete Point", key="delete_point"):
                          st.session_state.manual_curve_points.pop(del_idx - 1)
                          st.rerun()

                # Build the default_curve from manual points
                default_curve = {
                    str(p["wind_speed"]): int(p["power"])
                    for p in st.session_state.manual_curve_points
                }

                # Show curve preview
                if len(default_curve) >= 2:
                    chart_data = pd.DataFrame(
                        [
                            {"Wind Speed (m/s)": float(k), "Power (kW)": v}
                            for k, v in sorted(
                                default_curve.items(), key=lambda x: float(x[0])
                            )
                        ]
                    )
                    st.line_chart(
                        chart_data, x="Wind Speed (m/s)", y="Power (kW)", height=180
                    )

                    max_power = max(default_curve.values())
                    st.caption(
                        f"Max Power: {max_power:,} kW | {len(default_curve)} points"
                    )

        if st.button("Create Turbine", key="create_new_turb", type="secondary"):
            # Create power curve if needed
            if curve_choice == "Create New":
                curve_result = api.create_power_curve(
                    f"{new_turb_type} Curve", default_curve
                )
                if curve_result:
                    new_curve_id = curve_result["id"]
                else:
                    st.error("Failed to create power curve")
                    st.stop()

            # Create turbine
            turb_result = api.create_wind_turbine(
                turbine_type=new_turb_type or None,
                hub_height=new_hub_height,
                nominal_power=new_nominal_power,
                power_curve_id=new_curve_id,
            )
            if turb_result and not turb_result.get("error"):
                st.success(f"✅ Created turbine: {new_turb_type}")
                st.session_state.selected_turbine_id = turb_result["id"]
                st.rerun()
            else:
                st.error("Failed to create turbine")

    st.divider()

    # Location selection
    st.markdown("### 📍 Select Location")

    loc_tab_existing, loc_tab_new = st.tabs(
        ["Use Existing Location", "Create New Location"]
    )

    with loc_tab_existing:
        if not all_locations:
            st.info(
                "No locations available. Create one in the 'Create New Location' tab."
            )
            selected_loc_id = None
        else:
            loc_opts = {
                f"({l['latitude']:.2f}, {l['longitude']:.2f})": l["id"]
                for l in all_locations
            }
            selected_loc = st.selectbox(
                "Select Location", list(loc_opts.keys()), key="existing_loc"
            )
            selected_loc_id = loc_opts[selected_loc] if selected_loc else None

    with loc_tab_new:
        col1, col2 = st.columns(2)
        with col1:
            new_lat = st.number_input(
                "Latitude", value=52.0, min_value=-90.0, max_value=90.0, key="new_lat"
            )
        with col2:
            new_lon = st.number_input(
                "Longitude", value=4.0, min_value=-180.0, max_value=180.0, key="new_lon"
            )

        st.markdown("**Quick Add:**")
        cols = st.columns(3)
        for i, loc in enumerate(PREDEFINED_LOCATIONS[:6]):
            with cols[i % 3]:
                if st.button(
                    f"📍 {loc['name']}",
                    key=f"quick_loc_{loc['name']}",
                    use_container_width=True,
                ):
                    result = api.create_location(
                        latitude=loc["latitude"], longitude=loc["longitude"]
                    )
                    if result:
                        st.success(f"Added {loc['name']}")
                        st.rerun()

        if st.button("Create Location", key="create_new_loc", type="secondary"):
            result = api.create_location(latitude=new_lat, longitude=new_lon)
            if result:
                st.success("✅ Location created!")
                st.rerun()

    st.divider()

    # Number of turbines
    st.markdown("### 🔢 Number of Turbines")
    num_turbines = st.number_input(
        "How many turbines at this location?",
        min_value=1,
        max_value=500,
        value=10,
        key="num_turbs",
    )

    # Add fleet button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("➕ Add Fleet", type="primary", use_container_width=True):
            turb_id = st.session_state.get("selected_turbine_id")
            loc_id = selected_loc_id if "selected_loc_id" in dir() else None

            # Reload to get latest
            all_locations = api.get_locations()
            all_turbines = api.get_wind_turbines()

            if not turb_id and all_turbines:
                turb_id = all_turbines[0]["id"]
            if not loc_id and all_locations:
                loc_id = all_locations[0]["id"]

            if turb_id and loc_id:
                result = api.create_fleet(
                    wind_farm_id=farm["id"],
                    wind_turbine_id=turb_id,
                    location_id=loc_id,
                    number_of_turbines=num_turbines,
                )
                if result:
                    st.success("✅ Fleet added!")
                    st.rerun()
                else:
                    st.error("Failed to add fleet")
            else:
                st.error("Please select or create a turbine and location first")

    st.divider()

    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()
    with col3:
        current_fleets = api.get_fleets(wind_farm_id=farm["id"])
        if current_fleets:
            if st.button("Next →", use_container_width=True, type="primary"):
                st.session_state.wizard_step = 3
                st.rerun()
        else:
            st.button("Next →", use_container_width=True, disabled=True)
            st.caption("Add at least one fleet to continue")

# ==================== STEP 3: Review & Finish ====================
elif current_step == 3:
    farm = st.session_state.wizard_farm
    st.subheader("✅ Review Your Wind Farm")

    fleets = api.get_fleets(wind_farm_id=farm["id"])

    # Summary card
    st.markdown(
        f"""
    <div style="background: rgba(15, 23, 42, 0.95); border: 3px solid #10b981; border-radius: 16px; padding: 2rem; margin-bottom: 1rem;">
        <h2 style="color: #10b981; margin-bottom: 1rem;">🏭 {farm["name"]}</h2>
        <p style="color: #cbd5e1;">{farm.get("description") or "No description"}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Fleet summary
    total_turbines = sum(f["number_of_turbines"] for f in fleets)
    total_capacity = sum(
        f["number_of_turbines"]
        * (f.get("wind_turbine", {}).get("nominal_power", 0) or 0)
        for f in fleets
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Turbines", total_turbines)
    with col2:
        st.metric("Total Capacity", f"{total_capacity:.1f} MW")
    with col3:
        st.metric(
            "Locations",
            len({f.get("location", {}).get("id") for f in fleets if f.get("location")}),
        )

    st.divider()

    st.markdown("### ⚡ Turbine Fleets")
    for fleet in fleets:
        turb = fleet.get("wind_turbine") or {}
        loc = fleet.get("location") or {}
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"**{fleet['number_of_turbines']}x {turb.get('turbine_type', 'Unknown')}**"
                )
                st.caption(
                    f"{turb.get('nominal_power', 0)} MW × {fleet['number_of_turbines']} = {turb.get('nominal_power', 0) * fleet['number_of_turbines']:.1f} MW"
                )
            with col2:
                st.markdown(
                    f"📍 ({loc.get('latitude', 0):.2f}, {loc.get('longitude', 0):.2f})"
                )

    st.divider()

    # Finish buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back to Edit", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()
    with col2:
        if st.button("➕ Create Another Farm", use_container_width=True):
            st.session_state.wizard_step = 1
            st.session_state.wizard_farm = None
            st.rerun()
    with col3:
        if st.button(
            "✅ Finish & View Farms", use_container_width=True, type="primary"
        ):
            st.session_state.wizard_step = 1
            st.session_state.wizard_farm = None
            st.switch_page("pages/2_🏭_Manage_Farms.py")
