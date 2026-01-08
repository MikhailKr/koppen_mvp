"""FastAPI application entry point."""

from fastapi import FastAPI
import uvicorn
from app.api.v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Platform for forecasting solar and wind generation",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Include API routers
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information.

    Returns:
        Basic API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)