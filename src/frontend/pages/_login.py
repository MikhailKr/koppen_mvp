"""Login and registration page."""

import streamlit as st

from frontend.auth import init_session_state, is_authenticated, login, register
from frontend.styles import inject_css

st.set_page_config(
    page_title="Login - Koppen",
    page_icon="⚡",
    layout="wide",
)

init_session_state()
inject_css(include_background=True)

if is_authenticated():
    st.switch_page("ℹ️_Info.py")

# Layout
col_spacer_left, col_form, col_spacer_right = st.columns([1, 2, 2])

with col_form:
    st.markdown(
        """
    <div style="text-align: center; margin-bottom: 2rem; margin-top: 3rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">⚡</div>
        <h1 style="margin-bottom: 0.25rem; font-size: 2.5rem;">Koppen</h1>
        <p style="color: #94a3b8 !important; font-size: 1.1rem;">Wind Power Forecasting</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login, st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")

        submitted = st.form_submit_button(
            "Sign In", use_container_width=True, type="primary"
        )

        if submitted:
            if not email or not password:
                st.error("Please fill in all fields")
            else:
                with st.spinner("Signing in..."):
                    if login(email, password):
                        st.success("Welcome back!")
                        st.switch_page("ℹ️_Info.py")
                    else:
                        st.error("Invalid email or password")

    with tab_register, st.form("register_form"):
        reg_full_name = st.text_input("Full Name", placeholder="John Doe")
        reg_email = st.text_input(
            "Email", placeholder="you@example.com", key="reg_email"
        )
        reg_password = st.text_input(
            "Password",
            type="password",
            placeholder="Min 6 characters",
            key="reg_password",
        )
        reg_password_confirm = st.text_input(
            "Confirm Password", type="password", placeholder="••••••••"
        )

        submitted = st.form_submit_button(
            "Create Account", use_container_width=True, type="primary"
        )

        if submitted:
            if not reg_email or not reg_password:
                st.error("Email and password are required")
            elif reg_password != reg_password_confirm:
                st.error("Passwords do not match")
            elif len(reg_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                with st.spinner("Creating account..."):
                    if register(reg_email, reg_password, reg_full_name or None):
                        st.success("Account created! Signing you in...")
                        if login(reg_email, reg_password):
                            st.switch_page("ℹ️_Info.py")
                    else:
                        st.error(
                            "Registration failed. Email may already be registered."
                        )

    st.markdown(
        """
    <p style='text-align: center; margin-top: 2rem;'>
        <a href='/' target='_self' style='color: #0ea5e9; text-decoration: none;'>← Back to Info</a>
    </p>
    """,
        unsafe_allow_html=True,
    )
