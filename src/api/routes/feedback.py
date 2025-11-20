from fastapi import APIRouter, HTTPException

from src.api.schemas.feedback import FeedbackRequest, FeedbackResponse
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    try:
        logger.info(
            "Feedback received",
            user_id=request.user_id,
            product_id=request.product_id,
            relevant=request.relevant,
            recommendation_id=request.recommendation_id,
        )

        return FeedbackResponse(
            success=True,
            message="Feedback recorded successfully",
        )

    except Exception as e:
        logger.error("Feedback error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

