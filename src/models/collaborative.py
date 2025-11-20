from typing import List, Tuple, Set, Optional
import numpy as np
import pandas as pd
import joblib
from implicit.als import AlternatingLeastSquares
from scipy.sparse import csr_matrix

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CollaborativeFilter:
    def __init__(
        self,
        factors: int = 50,
        iterations: int = 15,
        regularization: float = 0.1,
        alpha: float = 1.0,
    ):
        self.factors = factors
        self.iterations = iterations
        self.regularization = regularization
        self.alpha = alpha
        self.model: Optional[AlternatingLeastSquares] = None
        self.user_to_idx: dict = {}
        self.idx_to_user: dict = {}
        self.product_to_idx: dict = {}
        self.idx_to_product: dict = {}

    def _prepare_matrix(self, df: pd.DataFrame) -> csr_matrix:
        unique_users = df["user_id"].unique()
        unique_products = df["product_id"].unique()

        self.user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
        self.idx_to_user = {idx: user_id for user_id, idx in self.user_to_idx.items()}

        self.product_to_idx = {product_id: idx for idx, product_id in enumerate(unique_products)}
        self.idx_to_product = {idx: product_id for product_id, idx in self.product_to_idx.items()}

        user_indices = df["user_id"].map(self.user_to_idx).values
        product_indices = df["product_id"].map(self.product_to_idx).values

        if "rating" in df.columns:
            ratings = df["rating"].values
            weights = ratings * self.alpha
        else:
            weights = np.ones(len(df)) * self.alpha

        matrix = csr_matrix(
            (weights, (user_indices, product_indices)),
            shape=(len(unique_users), len(unique_products)),
        )

        return matrix

    def fit(self, train_df: pd.DataFrame) -> None:
        logger.info("Training collaborative filter", rows=len(train_df))
        matrix = self._prepare_matrix(train_df)

        self.model = AlternatingLeastSquares(
            factors=self.factors,
            iterations=self.iterations,
            regularization=self.regularization,
            random_state=42,
        )

        self.model.fit(matrix)
        logger.info("Collaborative filter trained")

    def recommend(
        self, user_id: str, top_k: int = 10, exclude_seen: Set[str] = None
    ) -> List[Tuple[str, float]]:
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        if user_id not in self.user_to_idx:
            logger.warning("User not found in training data", user_id=user_id)
            return []

        exclude_seen = exclude_seen or set()
        user_idx = self.user_to_idx[user_id]

        product_indices, scores = self.model.recommend(
            user_idx,
            self.model.user_factors[user_idx],
            N=top_k + len(exclude_seen),
            filter_already_liked_items=False,
        )

        recommendations = []
        for product_idx, score in zip(product_indices, scores):
            product_id = self.idx_to_product.get(product_idx)
            if product_id and product_id not in exclude_seen:
                recommendations.append((product_id, float(score)))
            if len(recommendations) >= top_k:
                break

        return recommendations

    def similar_items(self, product_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        if product_id not in self.product_to_idx:
            logger.warning("Product not found in training data", product_id=product_id)
            return []

        product_idx = self.product_to_idx[product_id]
        similar_indices, scores = self.model.similar_items(product_idx, N=top_k + 1)

        recommendations = []
        for similar_idx, score in zip(similar_indices, scores):
            if similar_idx == product_idx:
                continue
            similar_product_id = self.idx_to_product.get(similar_idx)
            if similar_product_id:
                recommendations.append((similar_product_id, float(score)))
            if len(recommendations) >= top_k:
                break

        return recommendations

    def save(self, file_path: str) -> None:
        logger.info("Saving collaborative filter", file_path=file_path)
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        model_data = {
            "model": self.model,
            "user_to_idx": self.user_to_idx,
            "idx_to_user": self.idx_to_user,
            "product_to_idx": self.product_to_idx,
            "idx_to_product": self.idx_to_product,
            "factors": self.factors,
            "iterations": self.iterations,
            "regularization": self.regularization,
            "alpha": self.alpha,
        }

        joblib.dump(model_data, file_path)
        logger.info("Collaborative filter saved")

    @classmethod
    def load(cls, file_path: str) -> "CollaborativeFilter":
        logger.info("Loading collaborative filter", file_path=file_path)
        model_data = joblib.load(file_path)

        instance = cls(
            factors=model_data["factors"],
            iterations=model_data["iterations"],
            regularization=model_data["regularization"],
            alpha=model_data["alpha"],
        )

        instance.model = model_data["model"]
        instance.user_to_idx = model_data["user_to_idx"]
        instance.idx_to_user = model_data["idx_to_user"]
        instance.product_to_idx = model_data["product_to_idx"]
        instance.idx_to_product = model_data["idx_to_product"]

        logger.info("Collaborative filter loaded")
        return instance

