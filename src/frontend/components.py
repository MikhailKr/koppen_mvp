"""Shared UI components for the Koppen frontend."""

import streamlit as st

from frontend.auth import is_authenticated, logout


def render_sidebar() -> None:
    """Render the common sidebar with branding and auth controls."""
    with st.sidebar:
        st.markdown("### ⚡ Koppen")
        st.caption("Wind Power Forecasting")

        st.divider()

        if is_authenticated():
            user = st.session_state.get("user", {})
            st.markdown(f"**{user.get('full_name') or user.get('email', 'User')}**")
            st.caption(user.get("email", ""))

            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                logout()
                st.rerun()
        else:
            st.info("Login to access all features")
            if st.button("🔐 Login", use_container_width=True, type="primary"):
                st.switch_page("pages/_login.py")


def require_auth() -> bool:
    """Check if user is authenticated, show login prompt if not. Returns True if authenticated."""
    if not is_authenticated():
        st.warning("Please login to access this page")
        if st.button("Go to Login", type="primary"):
            st.switch_page("pages/_login.py")
        st.stop()
        return False
    return True



