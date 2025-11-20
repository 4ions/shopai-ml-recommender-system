from typing import List
from pydantic import BaseModel, Field

from src.api.schemas.search import ProductResult


class RecommendationRequest(BaseModel):
    user_id: str = Field(..., description="User ID for recommendations")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of recommendations to return")
    exclude_seen: bool = Field(default=True, description="Exclude items user has already interacted with")
    include_metadata: bool = Field(default=True, description="Include product metadata in response")
    diversify: bool = Field(default=False, description="Apply diversification to recommendations")


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[ProductResult]
    model_version: str = "v1.0"
    inference_time_ms: float

