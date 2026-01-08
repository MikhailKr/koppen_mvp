# Koppen MVP

Platform for forecasting solar and wind generation.

## Quick Start

```bash
# Create virtual environment with uv
uv venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
uv pip install -e ".[dev]"

# Run the server
cd src
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /` - API info
- `GET /api/v1/health` - Health check
- `GET /api/v1/ready` - Readiness check
- `GET /docs` - Swagger UI

