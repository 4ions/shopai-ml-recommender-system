from typing import List, Tuple, Dict, Any, Callable
import numpy as np
import pandas as pd

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RecommenderEvaluator:
    def __init__(self, test_df: pd.DataFrame):
        self.test_df = test_df
        self.user_ground_truth = self._build_ground_truth()

    def _build_ground_truth(self) -> Dict[str, List[str]]:
        ground_truth = {}
        for user_id, user_df in self.test_df.groupby("user_id"):
            relevant_items = user_df[user_df["rating"] >= 4]["product_id"].tolist()
            ground_truth[user_id] = relevant_items
        return ground_truth

    def precision_at_k(
        self, recommendations: List[str], ground_truth: List[str], k: int
    ) -> float:
        if k == 0:
            return 0.0

        top_k = recommendations[:k]
        relevant = set(ground_truth)
        hits = sum(1 for item in top_k if item in relevant)
        return hits / k

    def recall_at_k(
        self, recommendations: List[str], ground_truth: List[str], k: int
    ) -> float:
        if len(ground_truth) == 0:
            return 0.0

        top_k = recommendations[:k]
        relevant = set(ground_truth)
        hits = sum(1 for item in top_k if item in relevant)
        return hits / len(ground_truth)

    def ndcg_at_k(
        self, recommendations: List[str], ground_truth: List[str], k: int
    ) -> float:
        if len(ground_truth) == 0:
            return 0.0

        top_k = recommendations[:k]
        relevant = set(ground_truth)

        dcg = 0.0
        for i, item in enumerate(top_k):
            if item in relevant:
                dcg += 1.0 / np.log2(i + 2)

        idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(ground_truth), k)))
        if idcg == 0:
            return 0.0

        return dcg / idcg

    def map_at_k(
        self, recommendations: List[str], ground_truth: List[str], k: int
    ) -> float:
        if len(ground_truth) == 0:
            return 0.0

        top_k = recommendations[:k]
        relevant = set(ground_truth)

        if not relevant:
            return 0.0

        precision_sum = 0.0
        hits = 0

        for i, item in enumerate(top_k):
            if item in relevant:
                hits += 1
                precision_sum += hits / (i + 1)

        return precision_sum / len(ground_truth) if len(ground_truth) > 0 else 0.0

    def coverage(self, all_recommendations: Dict[str, List[str]], catalog_size: int) -> float:
        recommended_items = set()
        for recommendations in all_recommendations.values():
            recommended_items.update(recommendations)

        return len(recommended_items) / catalog_size if catalog_size > 0 else 0.0

    def evaluate(
        self,
        recommender_func: Callable[[str, int], List[Tuple[str, float]]],
        k_values: List[int] = [5, 10, 20],
    ) -> Dict[str, Any]:
        logger.info("Starting evaluation", k_values=k_values)

        results = {}
        for k in k_values:
            results[f"precision@{k}"] = []
            results[f"recall@{k}"] = []
            results[f"ndcg@{k}"] = []
            results[f"map@{k}"] = []

        for user_id, ground_truth in self.user_ground_truth.items():
            try:
                recommendations_with_scores = recommender_func(user_id, top_k=max(k_values))
                recommendations = [item_id for item_id, _ in recommendations_with_scores]

                for k in k_values:
                    results[f"precision@{k}"].append(
                        self.precision_at_k(recommendations, ground_truth, k)
                    )
                    results[f"recall@{k}"].append(
                        self.recall_at_k(recommendations, ground_truth, k)
                    )
                    results[f"ndcg@{k}"].append(
                        self.ndcg_at_k(recommendations, ground_truth, k)
                    )
                    results[f"map@{k}"].append(
                        self.map_at_k(recommendations, ground_truth, k)
                    )

            except Exception as e:
                logger.warning("Error evaluating user", user_id=user_id, error=str(e))
                for k in k_values:
                    results[f"precision@{k}"].append(0.0)
                    results[f"recall@{k}"].append(0.0)
                    results[f"ndcg@{k}"].append(0.0)
                    results[f"map@{k}"].append(0.0)

        summary = {}
        for metric, values in results.items():
            summary[metric] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "median": float(np.median(values)),
            }

        logger.info("Evaluation complete", summary=summary)
        return summary

