"""Info page - main landing page."""

import streamlit as st

from frontend.auth import init_session_state, is_authenticated
from frontend.components import render_sidebar
from frontend.styles import inject_css

# Page configuration
st.set_page_config(
    page_title="Koppen - Wind Power Forecasting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
inject_css()
render_sidebar()

# Custom card CSS
st.markdown("""
<style>
.feature-card {
    background: rgba(15, 23, 42, 0.95);
    border: 3px solid #0ea5e9;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 0 20px rgba(14, 165, 233, 0.4), 0 4px 20px rgba(0, 0, 0, 0.5);
    transition: all 0.3s ease;
    min-height: 200px;
}
.feature-card:hover {
    border-color: #38bdf8;
    box-shadow: 0 0 30px rgba(14, 165, 233, 0.6), 0 6px 25px rgba(0, 0, 0, 0.6);
    transform: translateY(-3px);
}
.feature-card h3 {
    color: #38bdf8 !important;
    font-size: 1.3rem;
    margin-bottom: 0.75rem;
    font-weight: 600;
}
.feature-card p {
    color: #e2e8f0 !important;
    font-size: 0.95rem;
    line-height: 1.6;
    margin: 0;
}
.coming-soon-card {
    background: rgba(15, 23, 42, 0.95);
    border: 3px solid #f59e0b;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.3), 0 4px 20px rgba(0, 0, 0, 0.5);
    min-height: 200px;
}
.coming-soon-card h3 {
    color: #fbbf24 !important;
    font-size: 1.3rem;
    margin-bottom: 0.75rem;
    font-weight: 600;
}
.coming-soon-card p {
    color: #e2e8f0 !important;
    font-size: 0.95rem;
    line-height: 1.6;
    margin: 0;
}
.coming-soon-badge {
    display: inline-block;
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    margin-top: 0.75rem;
}
</style>
""", unsafe_allow_html=True)

# Main content
st.markdown("""
<div class="hero">
    <p class="hero-title">Wind Power Forecasting</p>
    <p class="hero-subtitle">
        Accurate power generation predictions using advanced weather-based models
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Features section
st.markdown("## ✨ Features")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>🏭 Wind Farm Management</h3>
        <p>Configure your wind farms with detailed turbine specifications, 
        locations, and power curves. Support for multi-turbine fleets 
        at different locations.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>🔮 Generation Forecasting</h3>
        <p>Generate accurate power output forecasts using real-time 
        weather data. Compare predictions against actual generation 
        to measure accuracy.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🌤️ Weather Integration</h3>
        <p>Real-time and historical weather data for any location. 
        Visualize wind speed, direction, temperature and more 
        with interactive charts.</p>
    </div>
    """, unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("""
    <div class="feature-card">
        <h3>📈 Power Curve Modeling</h3>
        <p>Import manufacturer power curves from the wind turbine 
        library or define custom curves. Accurate modeling of 
        turbine performance.</p>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown("""
    <div class="feature-card">
        <h3>🔬 Synthetic Data Lab</h3>
        <p>Generate realistic synthetic generation data for testing 
        and validation. Add noise, simulate outages, and explore 
        different scenarios.</p>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Accuracy Metrics</h3>
        <p>Compare forecasts against actual generation data. 
        Calculate MAE, RMSE, MAPE and bias metrics to track 
        forecast performance.</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Coming soon section
st.markdown("## 🚀 Coming Soon")

col_soon1, col_soon2, _ = st.columns([1, 1, 1])

with col_soon1:
    st.markdown("""
    <div class="coming-soon-card">
        <h3>☀️ Solar Power Forecasting</h3>
        <p>Predict solar energy generation using irradiance data, 
        panel specifications, and weather forecasts. Coming in 
        the next release!</p>
        <span class="coming-soon-badge">🔜 In Development</span>
    </div>
    """, unsafe_allow_html=True)

with col_soon2:
    st.markdown("""
    <div class="coming-soon-card">
        <h3>🔄 Automated Pipelines</h3>
        <p>Schedule automatic forecast generation with Airflow. 
        Set up recurring forecasts and data collection for 
        your wind farms.</p>
        <span class="coming-soon-badge">🔜 In Development</span>
    </div>
    """, unsafe_allow_html=True)

# CTA for non-authenticated users
if not is_authenticated():
    st.divider()
    st.markdown("### Get Started")
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        if st.button("Login", use_container_width=True, type="primary", key="cta_login"):
            st.switch_page("pages/_login.py")
    with col2:
        if st.button("Register", use_container_width=True, key="cta_register"):
            st.switch_page("pages/_login.py")
