"""Shared styles and theme for the Koppen MVP frontend."""

import base64
from pathlib import Path

# Color palette - inspired by wind/energy themes
COLORS = {
    "primary": "#0ea5e9",      # Sky blue
    "primary_dark": "#0284c7",
    "secondary": "#10b981",    # Emerald green
    "accent": "#f59e0b",       # Amber
    "background": "#0f172a",   # Slate 900
    "surface": "#1e293b",      # Slate 800
    "surface_light": "#334155", # Slate 700
    "text": "#f8fafc",         # Slate 50
    "text_muted": "#94a3b8",   # Slate 400
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
}


_CACHED_BG_IMAGE: str | None = None


def get_background_image_base64() -> str:
    """Load the background image and return as base64. Cached after first load."""
    global _CACHED_BG_IMAGE
    if _CACHED_BG_IMAGE is not None:
        return _CACHED_BG_IMAGE
    
    try:
        image_path = Path(__file__).parent / "assets" / "image1.png"
        if image_path.exists():
            with open(image_path, "rb") as f:
                _CACHED_BG_IMAGE = base64.b64encode(f.read()).decode()
                return _CACHED_BG_IMAGE
    except Exception:
        pass
    _CACHED_BG_IMAGE = ""
    return ""


def get_global_css(include_background: bool = True) -> str:
    """Generate global CSS with optional background image."""
    bg_css = ""
    if include_background:
        bg_image = get_background_image_base64()
        if bg_image:
            bg_css = f"""
/* Full page background image */
.stApp {{
    background-image: url('data:image/png;base64,{bg_image}');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}}

.stApp::before {{
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(15, 23, 42, 0.8);
    z-index: 0;
    pointer-events: none;
}}

[data-testid="stAppViewContainer"] > .main {{
    position: relative;
    z-index: 1;
}}
"""

    return f"""
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

/* Root variables */
:root {{
    --primary: #0ea5e9;
    --primary-dark: #0284c7;
    --secondary: #10b981;
    --accent: #f59e0b;
    --bg-dark: #0f172a;
    --surface: #1e293b;
    --surface-light: #334155;
    --text: #f8fafc;
    --text-muted: #cbd5e1;
}}

/* Style the top header to match dark theme */
header[data-testid="stHeader"] {{
    background: transparent !important;
    border-bottom: none !important;
}}

/* Keep hamburger menu visible for sidebar toggle */
#MainMenu {{
    visibility: visible !important;
}}

/* Hide footer */
footer {{
    visibility: hidden !important;
}}

/* Main container styling */
.stApp {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}}

{bg_css}

/* All text should be light colored */
.stApp, .stApp p, .stApp span, .stApp div, .stApp label {{
    color: #f1f5f9 !important;
}}

/* Headers - bright white */
h1, h2, h3, h4, h5, h6 {{
    font-weight: 600 !important;
    color: #ffffff !important;
}}

/* Markdown text */
.stMarkdown, .stMarkdown p {{
    color: #e2e8f0 !important;
}}

/* Card containers with borders - highly visible styling */
[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: rgba(15, 23, 42, 0.95) !important;
    border: 2px solid #0ea5e9 !important;
    border-radius: 16px !important;
    backdrop-filter: blur(12px);
    box-shadow: 0 0 15px rgba(14, 165, 233, 0.3), 0 4px 20px rgba(0, 0, 0, 0.4) !important;
    transition: all 0.3s ease;
}}

[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    border-color: #38bdf8 !important;
    box-shadow: 0 0 25px rgba(14, 165, 233, 0.5), 0 6px 25px rgba(0, 0, 0, 0.5) !important;
    transform: translateY(-2px);
}}

/* Bordered container content */
[data-testid="stVerticalBlockBorderWrapper"] h3 {{
    color: #38bdf8 !important;
    text-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
}}

[data-testid="stVerticalBlockBorderWrapper"] p {{
    color: #e2e8f0 !important;
    line-height: 1.6;
}}

/* Hero section */
.hero {{
    text-align: center;
    padding: 2rem 0;
}}

.hero-title {{
    font-size: 2.75rem;
    font-weight: 700;
    background: linear-gradient(135deg, #0ea5e9 0%, #10b981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
}}

.hero-subtitle {{
    font-size: 1.1rem;
    color: #cbd5e1 !important;
    max-width: 600px;
    margin: 0 auto;
}}

/* Sidebar styling */
section[data-testid="stSidebar"] {{
    background: rgba(30, 41, 59, 0.98) !important;
}}

section[data-testid="stSidebar"] .stButton button {{
    border-radius: 8px !important;
}}

/* Sidebar navigation links */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    color: #e2e8f0 !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
    color: #ffffff !important;
    background: rgba(255, 255, 255, 0.1) !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {{
    background: rgba(14, 165, 233, 0.2) !important;
    color: #0ea5e9 !important;
}}

/* Sidebar text */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: #e2e8f0 !important;
}}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
    background: transparent !important;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 8px 8px 0 0;
    padding: 0.75rem 1.25rem;
    color: #94a3b8 !important;
}}

.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: #0ea5e9 !important;
}}

/* Remove default top padding */
.block-container {{
    padding-top: 1rem !important;
}}

/* Info boxes */
.stAlert {{
    background: rgba(14, 165, 233, 0.1) !important;
    border: 1px solid rgba(14, 165, 233, 0.3) !important;
    border-radius: 8px !important;
}}

.stAlert p {{
    color: #e2e8f0 !important;
}}

/* Input fields */
.stTextInput input, .stSelectbox > div > div {{
    background: rgba(51, 65, 85, 0.8) !important;
    border: 1px solid rgba(148, 163, 184, 0.3) !important;
    color: #f1f5f9 !important;
}}

.stTextInput label, .stSelectbox label {{
    color: #cbd5e1 !important;
}}

/* Buttons */
.stButton button[kind="primary"] {{
    background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
    border: none !important;
}}

.stButton button[kind="secondary"] {{
    background: rgba(51, 65, 85, 0.8) !important;
    border: 1px solid rgba(148, 163, 184, 0.3) !important;
    color: #f1f5f9 !important;
}}

/* Metrics */
[data-testid="stMetricValue"] {{
    font-weight: 600 !important;
    color: #0ea5e9 !important;
}}

[data-testid="stMetricLabel"] {{
    color: #94a3b8 !important;
}}

/* Dividers */
hr {{
    border-color: rgba(148, 163, 184, 0.2) !important;
}}

/* Data tables - ensure dark styling everywhere */
.stDataFrame {{
    border-radius: 8px !important;
    overflow: hidden;
}}

/* Force all dataframe text to be white/light - very aggressive targeting */
.stDataFrame,
.stDataFrame *,
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] *,
[data-testid="stExpander"] .stDataFrame,
[data-testid="stExpander"] .stDataFrame * {{
    color: #f1f5f9 !important;
}}

/* Glide Data Grid - the new Streamlit dataframe component */
[data-testid="stDataFrame"] canvas {{
    filter: none !important;
}}

/* Target the actual data grid container */
[data-testid="stDataFrame"] [data-testid="data-grid-canvas"],
[data-testid="stDataFrame"] .dvn-underlay,
[data-testid="stDataFrame"] .dvn-scroller {{
    background: #1e293b !important;
}}

/* Cell text rendering - force white text via CSS variables */
[data-testid="stDataFrame"] {{
    --gdg-text-dark: #f1f5f9 !important;
    --gdg-text-medium: #e2e8f0 !important;
    --gdg-text-light: #cbd5e1 !important;
    --gdg-bg-cell: #1e293b !important;
    --gdg-bg-header: #334155 !important;
    --gdg-bg-header-hovered: #475569 !important;
    --gdg-border-color: rgba(148, 163, 184, 0.3) !important;
    --gdg-accent-color: #0ea5e9 !important;
    --gdg-accent-fg: #ffffff !important;
    --gdg-accent-light: rgba(14, 165, 233, 0.2) !important;
}}

/* Force header text color */
[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stDataFrame"] th {{
    color: #f1f5f9 !important;
    background: #334155 !important;
}}

/* Force cell text color */
[data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] td {{
    color: #e2e8f0 !important;
    background: #1e293b !important;
}}

/* Row numbers column */
[data-testid="stDataFrame"] [data-testid="glide-row-marker"] {{
    color: #94a3b8 !important;
    background: #1e293b !important;
}}

/* Selection and hover states */
[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {{
    background: #334155 !important;
}}

/* Expanders */
.streamlit-expanderHeader {{
    font-weight: 500 !important;
    border-radius: 8px !important;
    background: rgba(51, 65, 85, 0.9) !important;
    color: #f1f5f9 !important;
}}

/* Expander content area */
[data-testid="stExpander"] {{
    background: rgba(30, 41, 59, 0.98) !important;
    border: 2px solid rgba(14, 165, 233, 0.4) !important;
    border-radius: 12px !important;
}}

[data-testid="stExpander"] > div {{
    background: rgba(30, 41, 59, 0.98) !important;
}}

[data-testid="stExpander"] details {{
    background: rgba(30, 41, 59, 0.98) !important;
}}

[data-testid="stExpander"] details > div {{
    background: rgba(30, 41, 59, 0.98) !important;
}}

/* All text inside expanders */
[data-testid="stExpander"] p,
[data-testid="stExpander"] span,
[data-testid="stExpander"] label,
[data-testid="stExpander"] div {{
    color: #f1f5f9 !important;
}}

[data-testid="stExpander"] strong {{
    color: #38bdf8 !important;
}}

[data-testid="stExpander"] [data-testid="stCaptionContainer"] {{
    color: #94a3b8 !important;
}}

[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {{
    color: #e2e8f0 !important;
}}

[data-testid="stExpander"] [data-testid="stMarkdownContainer"] strong {{
    color: #38bdf8 !important;
}}

/* Charts */
.stAltairChart {{
    background: transparent !important;
}}

/* Caption text */
.stCaption, [data-testid="stCaptionContainer"] {{
    color: #94a3b8 !important;
}}
</style>
"""


# Keep backward compatibility
GLOBAL_CSS = get_global_css(include_background=True)


def inject_css(include_background: bool = True) -> None:
    """Inject global CSS into the Streamlit app."""
    import streamlit as st
    st.markdown(get_global_css(include_background), unsafe_allow_html=True)
