from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProductResult(BaseModel):
    product_id: str
    score: float
    name: str
    category: str
    description: str
    avg_rating: float
    total_interactions: int


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query text")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional filters (category, min_rating, min_interactions)"
    )


class SearchResponse(BaseModel):
    results: List[ProductResult]
    query_embedding_time_ms: float
    search_time_ms: float
    total_time_ms: float

