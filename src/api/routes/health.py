from fastapi import APIRouter

from src.api.schemas.health import HealthResponse
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    checks = {
        "api": "healthy",
    }

    try:
        from src.api.main import app

        if hasattr(app.state, "hybrid_recommender"):
            checks["models"] = "loaded"
        else:
            checks["models"] = "not_loaded"

        if hasattr(app.state, "vector_store"):
            checks["vector_store"] = "loaded"
        else:
            checks["vector_store"] = "not_loaded"

    except Exception as e:
        logger.error("Health check error", error=str(e))
        checks["error"] = str(e)

    status = "healthy" if all(v != "not_loaded" for v in checks.values() if isinstance(v, str)) else "degraded"

    return HealthResponse(status=status, checks=checks)

