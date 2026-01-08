"""Frontend configuration."""

import os

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_V1_PREFIX = "/api/v1"

# Predefined locations for quick selection
PREDEFINED_LOCATIONS = [
    {"name": "Berlin, Germany", "latitude": 52.52, "longitude": 13.405},
    {"name": "Copenhagen, Denmark", "latitude": 55.6761, "longitude": 12.5683},
    {"name": "Amsterdam, Netherlands", "latitude": 52.3676, "longitude": 4.9041},
    {"name": "London, UK", "latitude": 51.5074, "longitude": -0.1278},
    {"name": "Paris, France", "latitude": 48.8566, "longitude": 2.3522},
    {"name": "Madrid, Spain", "latitude": 40.4168, "longitude": -3.7038},
    {"name": "Stockholm, Sweden", "latitude": 59.3293, "longitude": 18.0686},
    {"name": "Oslo, Norway", "latitude": 59.9139, "longitude": 10.7522},
]
