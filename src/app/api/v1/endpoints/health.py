"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check if the API is running.

    Returns:
        Health status response.
    """
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Check if the API is ready to accept requests.

    Returns:
        Readiness status response.
    """
    # TODO: Add database connectivity check when PostgreSQL is added
    return {"status": "ready"}
