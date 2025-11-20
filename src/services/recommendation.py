from typing import List, Tuple, Optional, Set
import time

from src.models.hybrid import HybridRecommender
from src.data.catalog import UserCatalog, ProductCatalog
from src.infrastructure.logging import get_logger
from src.infrastructure.metrics import model_inference_duration_seconds
from src.infrastructure.cache import cache

logger = get_logger(__name__)


class RecommendationService:
    def __init__(
        self,
        hybrid_recommender: HybridRecommender,
        user_catalog: UserCatalog,
        product_catalog: ProductCatalog,
    ):
        self.hybrid_recommender = hybrid_recommender
        self.user_catalog = user_catalog
        self.product_catalog = product_catalog

    def _get_user_history(self, user_id: str) -> List[str]:
        user_stats = self.user_catalog.get_user_stats(user_id)
        if not user_stats:
            return []
        
        try:
            from src.data.ingestion import load_from_local
            import pandas as pd
            df = load_from_local("data/processed/ratings.parquet")
            user_transactions = df[df["user_id"] == user_id]
            return user_transactions["product_id"].tolist()
        except Exception as e:
            logger.warning("Could not load user history", user_id=user_id, error=str(e))
            return []

    def get_recommendations(
        self,
        user_id: str,
        top_k: int = 10,
        exclude_seen: bool = True,
        diversify: bool = False,
    ) -> List[Tuple[str, float]]:
        start_time = time.time()

        cache_key = f"recommendations:{user_id}:{top_k}:{exclude_seen}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug("Cache hit", user_id=user_id)
            return cached_result

        if user_id not in self.user_catalog.user_to_idx:
            logger.warning("User not found", user_id=user_id)
            return []

        user_history = self._get_user_history(user_id) if exclude_seen else None
        exclude_seen_set = set(user_history) if exclude_seen and user_history else set()

        recommendations = self.hybrid_recommender.recommend(
            user_id=user_id,
            user_history=user_history,
            top_k=top_k * 2 if diversify else top_k,
            exclude_seen=exclude_seen_set,
        )

        if diversify:
            recommendations = self.hybrid_recommender.diversify(recommendations)

        recommendations = recommendations[:top_k]

        inference_time = time.time() - start_time
        model_inference_duration_seconds.labels(model_type="hybrid", operation="recommend").observe(
            inference_time
        )

        cache.set(cache_key, recommendations, ttl=300)

        logger.info(
            "Recommendations generated",
            user_id=user_id,
            count=len(recommendations),
            inference_time_ms=inference_time * 1000,
        )

        return recommendations

    def get_recommendations_with_metadata(
        self,
        user_id: str,
        top_k: int = 10,
        exclude_seen: bool = True,
        diversify: bool = False,
    ) -> List[dict]:
        recommendations = self.get_recommendations(
            user_id=user_id, top_k=top_k, exclude_seen=exclude_seen, diversify=diversify
        )

        results = []
        for product_id, score in recommendations:
            metadata = self.product_catalog.get_product_metadata(product_id)
            stats = self.product_catalog.get_product_stats(product_id)

            results.append(
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

        return results

