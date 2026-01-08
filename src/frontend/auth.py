"""Authentication utilities for Streamlit."""

import streamlit as st

from frontend.api_client import APIClient


def init_session_state() -> None:
    """Initialize session state variables."""
    if "token" not in st.session_state:
        st.session_state.token = None
    if "user" not in st.session_state:
        st.session_state.user = None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get("token") is not None


def login(email: str, password: str) -> bool:
    """Attempt to login user.

    Args:
        email: User email.
        password: User password.

    Returns:
        True if login successful.
    """
    client = APIClient()
    result = client.login(email, password)

    if result:
        st.session_state.token = result["access_token"]
        # Fetch user info
        client_auth = APIClient(token=result["access_token"])
        user = client_auth.get_current_user()
        st.session_state.user = user
        return True
    return False


def register(email: str, password: str, full_name: str | None = None) -> bool:
    """Register a new user.

    Args:
        email: User email.
        password: User password.
        full_name: Optional full name.

    Returns:
        True if registration successful.
    """
    client = APIClient()
    result = client.register(email, password, full_name)
    return result is not None


def logout() -> None:
    """Logout current user."""
    st.session_state.token = None
    st.session_state.user = None


def require_auth() -> bool:
    """Require authentication, redirect to login if not authenticated.

    Returns:
        True if authenticated.
    """
    if not is_authenticated():
        st.warning("Please login to access this page.")
        st.switch_page("pages/9_🔐_Login.py")
        return False
    return True

