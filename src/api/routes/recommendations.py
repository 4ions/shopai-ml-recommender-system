from fastapi import APIRouter, HTTPException, Depends

from src.api.schemas.recommendations import RecommendationRequest, RecommendationResponse
from src.services.recommendation import RecommendationService
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


def get_recommendation_service() -> RecommendationService:
    from src.api.main import app
    return app.state.recommendation_service


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    try:
        import time
        start_time = time.time()

        recommendations = recommendation_service.get_recommendations_with_metadata(
            user_id=request.user_id,
            top_k=request.top_k,
            exclude_seen=request.exclude_seen,
            diversify=request.diversify,
        )

        inference_time = (time.time() - start_time) * 1000

        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendations,
            model_version="v1.0",
            inference_time_ms=inference_time,
        )

    except KeyError as e:
        logger.warning("User not found", user_id=request.user_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"User not found: {request.user_id}")
    except Exception as e:
        logger.error("Recommendation error", user_id=request.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

