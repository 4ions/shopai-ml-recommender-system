from typing import List, Tuple, Set
import pandas as pd
import numpy as np

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class PopularityBaseline:
    def __init__(self, transactions_df: pd.DataFrame):
        self.transactions_df = transactions_df
        self.popularity_scores = self._compute_popularity()

    def _compute_popularity(self) -> pd.Series:
        product_popularity = self.transactions_df.groupby("product_id")["rating"].agg(
            ["count", "mean"]
        )
        product_popularity["score"] = (
            product_popularity["count"] * product_popularity["mean"]
        )
        return product_popularity["score"].sort_values(ascending=False)

    def recommend(self, top_k: int = 10, exclude_seen: Set[str] = None) -> List[Tuple[str, float]]:
        exclude_seen = exclude_seen or set()
        recommendations = [
            (product_id, float(score))
            for product_id, score in self.popularity_scores.items()
            if product_id not in exclude_seen
        ][:top_k]
        return recommendations


class UserPopularityBaseline:
    def __init__(self, transactions_df: pd.DataFrame):
        self.transactions_df = transactions_df
        self.user_popularity = self._compute_user_popularity()

    def _compute_user_popularity(self) -> dict:
        user_popularity = {}
        for user_id, user_df in self.transactions_df.groupby("user_id"):
            product_scores = user_df.groupby("product_id")["rating"].agg(["count", "mean"])
            product_scores["score"] = product_scores["count"] * product_scores["mean"]
            user_popularity[user_id] = product_scores["score"].sort_values(ascending=False)
        return user_popularity

    def recommend(
        self, user_id: str, top_k: int = 10, exclude_seen: Set[str] = None
    ) -> List[Tuple[str, float]]:
        exclude_seen = exclude_seen or set()
        if user_id not in self.user_popularity:
            return []

        recommendations = [
            (product_id, float(score))
            for product_id, score in self.user_popularity[user_id].items()
            if product_id not in exclude_seen
        ][:top_k]
        return recommendations

