from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from src.api.schemas.search import SearchRequest, SearchResponse
from src.services.search import SearchService
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search"])


def get_search_service() -> SearchService:
    from src.api.main import app
    return app.state.search_service


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
):
    try:
        results, timing = search_service.search_with_metadata(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )

        return SearchResponse(
            results=results,
            query_embedding_time_ms=timing["query_embedding_time_ms"],
            search_time_ms=timing["search_time_ms"],
            total_time_ms=timing["total_time_ms"],
        )

    except Exception as e:
        logger.error("Search error", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

