from typing import Dict, List, Any
import pandas as pd
import json

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class UserCatalog:
    def __init__(self, transactions_df: pd.DataFrame):
        self.user_stats = self._compute_user_stats(transactions_df)
        self.user_to_idx: Dict[str, int] = {}
        self.idx_to_user: Dict[int, str] = {}

        unique_users = transactions_df["user_id"].unique()
        for idx, user_id in enumerate(unique_users):
            self.user_to_idx[user_id] = idx
            self.idx_to_user[idx] = user_id

    def _compute_user_stats(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        stats = df.groupby("user_id").agg(
            total_interactions=("rating", "count"),
            avg_rating=("rating", "mean"),
            min_rating=("rating", "min"),
            max_rating=("rating", "max"),
        ).to_dict(orient="index")

        return {str(k): {str(k2): float(v2) if isinstance(v2, (int, float)) else v2 for k2, v2 in v.items()} for k, v in stats.items()}

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        return self.user_stats.get(user_id, {})

    def get_user_idx(self, user_id: str) -> int:
        return self.user_to_idx.get(user_id, -1)

    def get_user_id(self, user_idx: int) -> str:
        return self.idx_to_user.get(user_idx, "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_stats": self.user_stats,
            "user_to_idx": self.user_to_idx,
            "idx_to_user": self.idx_to_user,
        }

    def save(self, file_path: str) -> None:
        logger.info("Saving user catalog", file_path=file_path)
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, file_path: str) -> "UserCatalog":
        logger.info("Loading user catalog", file_path=file_path)
        with open(file_path, "r") as f:
            data = json.load(f)

        catalog = cls.__new__(cls)
        catalog.user_stats = data["user_stats"]
        catalog.user_to_idx = {k: int(v) for k, v in data["user_to_idx"].items()}
        catalog.idx_to_user = {int(k): v for k, v in data["idx_to_user"].items()}
        return catalog


class ProductCatalog:
    def __init__(self, transactions_df: pd.DataFrame, products_df: pd.DataFrame):
        self.product_stats = self._compute_product_stats(transactions_df)
        self.product_metadata = self._load_product_metadata(products_df)
        self.product_to_idx: Dict[str, int] = {}
        self.idx_to_product: Dict[int, str] = {}

        unique_products = transactions_df["product_id"].unique()
        for idx, product_id in enumerate(unique_products):
            self.product_to_idx[product_id] = idx
            self.idx_to_product[idx] = product_id

    def _compute_product_stats(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        stats = df.groupby("product_id").agg(
            total_interactions=("rating", "count"),
            avg_rating=("rating", "mean"),
            min_rating=("rating", "min"),
            max_rating=("rating", "max"),
        ).to_dict(orient="index")

        return {str(k): {str(k2): float(v2) if isinstance(v2, (int, float)) else v2 for k2, v2 in v.items()} for k, v in stats.items()}

    def _load_product_metadata(self, df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
        metadata = {}
        for _, row in df.iterrows():
            product_id = str(row["product_id"])
            metadata[product_id] = {
                "category": str(row.get("category", "")),
                "name": str(row.get("name", "")),
                "description": str(row.get("description", "")),
            }
        return metadata

    def get_product_stats(self, product_id: str) -> Dict[str, Any]:
        return self.product_stats.get(product_id, {})

    def get_product_metadata(self, product_id: str) -> Dict[str, str]:
        return self.product_metadata.get(product_id, {})

    def get_product_idx(self, product_id: str) -> int:
        return self.product_to_idx.get(product_id, -1)

    def get_product_id(self, product_idx: int) -> str:
        return self.idx_to_product.get(product_idx, "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_stats": self.product_stats,
            "product_metadata": self.product_metadata,
            "product_to_idx": self.product_to_idx,
            "idx_to_product": self.idx_to_product,
        }

    def save(self, file_path: str) -> None:
        logger.info("Saving product catalog", file_path=file_path)
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, file_path: str) -> "ProductCatalog":
        logger.info("Loading product catalog", file_path=file_path)
        with open(file_path, "r") as f:
            data = json.load(f)

        catalog = cls.__new__(cls)
        catalog.product_stats = data["product_stats"]
        catalog.product_metadata = data["product_metadata"]
        catalog.product_to_idx = {k: int(v) for k, v in data["product_to_idx"].items()}
        catalog.idx_to_product = {int(k): v for k, v in data["idx_to_product"].items()}
        return catalog

