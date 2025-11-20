from typing import Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    product_id: str = Field(..., description="Product ID")
    relevant: bool = Field(..., description="Whether the recommendation was relevant")
    recommendation_id: Optional[str] = Field(default=None, description="Optional recommendation ID for tracking")


class FeedbackResponse(BaseModel):
    success: bool
    message: str

