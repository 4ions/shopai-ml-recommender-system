from typing import List, Tuple, Optional, Dict, Any
import time
import numpy as np
from openai import OpenAI

from src.services.vector_store import FAISSVectorStore
from src.models.embeddings import get_embedding
from src.data.catalog import ProductCatalog
from src.config.settings import settings
from src.infrastructure.logging import get_logger
from src.infrastructure.metrics import (
    model_inference_duration_seconds,
    openai_api_calls_total,
)
from src.infrastructure.cache import cache

logger = get_logger(__name__)


class SearchService:
    def __init__(
        self, vector_store: FAISSVectorStore, product_catalog: ProductCatalog, openai_client: Optional[OpenAI] = None
    ):
        self.vector_store = vector_store
        self.product_catalog = product_catalog
        self.openai_client = openai_client or OpenAI(api_key=settings.openai_api_key)

    def _get_query_embedding(self, query: str) -> np.ndarray:
        cache_key = f"query_embedding:{hash(query)}"
        cached_embedding = cache.get(cache_key)
        if cached_embedding is not None:
            return np.array(cached_embedding)

        embedding = get_embedding(self.openai_client, query)
        embedding_array = np.array(embedding, dtype=np.float32)

        cache.set(cache_key, embedding_array.tolist(), ttl=3600)

        return embedding_array

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Tuple[str, float]], Dict[str, float]]:
        start_time = time.time()

        embedding_start = time.time()
        query_embedding = self._get_query_embedding(query)
        embedding_time = time.time() - embedding_start

        search_start = time.time()
        results = self.vector_store.search(query_embedding, top_k=top_k * 2 if filters else top_k)
        search_time = time.time() - search_start

        if filters:
            results = self._apply_filters(results, filters)
            results = results[:top_k]

        total_time = time.time() - start_time

        model_inference_duration_seconds.labels(model_type="vector_search", operation="search").observe(
            total_time
        )

        logger.info(
            "Search completed",
            query=query[:50],
            results_count=len(results),
            embedding_time_ms=embedding_time * 1000,
            search_time_ms=search_time * 1000,
            total_time_ms=total_time * 1000,
        )

        return results, {
            "query_embedding_time_ms": embedding_time * 1000,
            "search_time_ms": search_time * 1000,
            "total_time_ms": total_time * 1000,
        }

    def _apply_filters(
        self, results: List[Tuple[str, float]], filters: Dict[str, Any]
    ) -> List[Tuple[str, float]]:
        filtered_results = []

        for product_id, score in results:
            metadata = self.product_catalog.get_product_metadata(product_id)
            stats = self.product_catalog.get_product_stats(product_id)

            if "category" in filters:
                if metadata.get("category") != filters["category"]:
                    continue

            if "min_rating" in filters:
                if stats.get("avg_rating", 0.0) < filters["min_rating"]:
                    continue

            if "min_interactions" in filters:
                if stats.get("total_interactions", 0) < filters["min_interactions"]:
                    continue

            filtered_results.append((product_id, score))

        return filtered_results

    def search_with_metadata(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[dict], Dict[str, float]]:
        results, timing = self.search(query, top_k=top_k, filters=filters)

        results_with_metadata = []
        for product_id, score in results:
            metadata = self.product_catalog.get_product_metadata(product_id)
            stats = self.product_catalog.get_product_stats(product_id)

            results_with_metadata.append(
                {
                    "product_id": product_id,
                    "score": score,
                    "name": metadata.get("name", ""),
                    "category": metadata.get("category", ""),
                    "description": metadata.get("description", ""),
                    "avg_rating": stats.get("avg_rating", 0.0),
                    "total_interactions": stats.get("total_interactions", 0),
                }
            )

        return results_with_metadata, timing

