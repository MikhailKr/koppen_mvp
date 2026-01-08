# Streamlit Frontend Dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install uv for faster package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies
RUN uv pip install --system streamlit httpx pandas altair pydeck

# Copy frontend code as 'frontend' package
COPY . ./frontend/

# Copy Streamlit config to correct location
RUN mkdir -p /app/.streamlit && cp /app/frontend/.streamlit/config.toml /app/.streamlit/config.toml

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "frontend/ℹ️_Info.py", "--server.address", "0.0.0.0", "--server.port", "8501"]

