from typing import List, Tuple, Set, Optional
import numpy as np

from src.models.collaborative import CollaborativeFilter
from src.services.vector_store import FAISSVectorStore
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class HybridRecommender:
    def __init__(
        self,
        collaborative_model: CollaborativeFilter,
        vector_store: FAISSVectorStore,
        alpha: float = 0.5,
        fusion_strategy: str = "weighted_sum",
    ):
        self.collaborative_model = collaborative_model
        self.vector_store = vector_store
        self.alpha = alpha
        self.fusion_strategy = fusion_strategy

    def _weighted_sum_fusion(
        self,
        collaborative_scores: List[Tuple[str, float]],
        semantic_scores: List[Tuple[str, float]],
    ) -> List[Tuple[str, float]]:
        collaborative_dict = {product_id: score for product_id, score in collaborative_scores}
        semantic_dict = {product_id: score for product_id, score in semantic_scores}

        all_products = set(collaborative_dict.keys()) | set(semantic_dict.keys())

        fused_scores = []
        for product_id in all_products:
            collab_score = collaborative_dict.get(product_id, 0.0)
            semantic_score = semantic_dict.get(product_id, 0.0)

            normalized_collab = self._normalize_score(collab_score, collaborative_scores)
            normalized_semantic = self._normalize_score(semantic_score, semantic_scores)

            fused_score = self.alpha * normalized_semantic + (1 - self.alpha) * normalized_collab
            fused_scores.append((product_id, fused_score))

        fused_scores.sort(key=lambda x: x[1], reverse=True)
        return fused_scores

    def _normalize_score(self, score: float, scores: List[Tuple[str, float]]) -> float:
        if not scores:
            return 0.0

        score_values = [s for _, s in scores]
        min_score = min(score_values)
        max_score = max(score_values)

        if max_score == min_score:
            return 0.5

        return (score - min_score) / (max_score - min_score)

    def _reciprocal_rank_fusion(
        self,
        collaborative_scores: List[Tuple[str, float]],
        semantic_scores: List[Tuple[str, float]],
        k: int = 60,
    ) -> List[Tuple[str, float]]:
        collaborative_ranks = {
            product_id: 1.0 / (k + rank)
            for rank, (product_id, _) in enumerate(collaborative_scores)
        }
        semantic_ranks = {
            product_id: 1.0 / (k + rank)
            for rank, (product_id, _) in enumerate(semantic_scores)
        }

        all_products = set(collaborative_ranks.keys()) | set(semantic_ranks.keys())

        fused_scores = []
        for product_id in all_products:
            rrf_score = collaborative_ranks.get(product_id, 0.0) + semantic_ranks.get(
                product_id, 0.0
            )
            fused_scores.append((product_id, rrf_score))

        fused_scores.sort(key=lambda x: x[1], reverse=True)
        return fused_scores

    def recommend(
        self,
        user_id: str,
        user_history: Optional[List[str]] = None,
        top_k: int = 10,
        exclude_seen: Set[str] = None,
    ) -> List[Tuple[str, float]]:
        exclude_seen = exclude_seen or set()

        collaborative_scores = self.collaborative_model.recommend(
            user_id, top_k=50, exclude_seen=exclude_seen
        )

        semantic_scores = []
        if user_history:
            user_history_embeddings = []
            for product_id in user_history[:10]:
                embedding = self.vector_store.get_embedding(product_id)
                if embedding is not None:
                    user_history_embeddings.append(embedding)

            if user_history_embeddings:
                avg_embedding = np.mean(user_history_embeddings, axis=0)
                semantic_scores = self.vector_store.search_by_vector(avg_embedding, top_k=50)

        if not semantic_scores:
            semantic_scores = self.vector_store.get_popular_items(top_k=50)

        if self.fusion_strategy == "weighted_sum":
            fused_scores = self._weighted_sum_fusion(collaborative_scores, semantic_scores)
        elif self.fusion_strategy == "rrf":
            fused_scores = self._reciprocal_rank_fusion(collaborative_scores, semantic_scores)
        else:
            raise ValueError(f"Unknown fusion strategy: {self.fusion_strategy}")

        recommendations = [
            (product_id, score)
            for product_id, score in fused_scores
            if product_id not in exclude_seen
        ][:top_k]

        return recommendations

    def diversify(
        self, recommendations: List[Tuple[str, float]], diversity_weight: float = 0.3
    ) -> List[Tuple[str, float]]:
        if len(recommendations) <= 1:
            return recommendations

        diversified = [recommendations[0]]
        remaining = recommendations[1:]

        while remaining and len(diversified) < len(recommendations):
            best_item = None
            best_score = float("-inf")

            for item_id, item_score in remaining:
                min_distance = min(
                    [
                        self.vector_store.distance(item_id, div_id)
                        for div_id, _ in diversified
                    ],
                    default=1.0,
                )

                diversified_score = (
                    (1 - diversity_weight) * item_score + diversity_weight * min_distance
                )

                if diversified_score > best_score:
                    best_score = diversified_score
                    best_item = (item_id, item_score)

            if best_item:
                diversified.append(best_item)
                remaining.remove(best_item)

        return diversified

