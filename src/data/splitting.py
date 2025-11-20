from typing import Tuple
import pandas as pd

from src.config.constants import TRAIN_SPLIT, VAL_SPLIT, TEST_SPLIT
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def temporal_split(
    df: pd.DataFrame,
    train_ratio: float = TRAIN_SPLIT,
    val_ratio: float = VAL_SPLIT,
    test_ratio: float = TEST_SPLIT,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info("Performing temporal split", train_ratio=train_ratio, val_ratio=val_ratio, test_ratio=test_ratio)

    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError("Split ratios must sum to 1.0")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)

    total_rows = len(df)
    train_end = int(total_rows * train_ratio)
    val_end = train_end + int(total_rows * val_ratio)

    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()

    logger.info(
        "Temporal split complete",
        train_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
    )

    return train_df, val_df, test_df


def validate_split(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> bool:
    logger.info("Validating split")

    train_users = set(train_df["user_id"].unique())
    train_products = set(train_df["product_id"].unique())

    val_users = set(val_df["user_id"].unique())
    val_products = set(val_df["product_id"].unique())

    test_users = set(test_df["user_id"].unique())
    test_products = set(test_df["product_id"].unique())

    val_cold_start_users = val_users - train_users
    val_cold_start_products = val_products - train_products

    test_cold_start_users = test_users - train_users
    test_cold_start_products = test_products - train_products

    if val_cold_start_users or val_cold_start_products:
        logger.warning(
            "Cold start in validation set",
            cold_start_users=len(val_cold_start_users),
            cold_start_products=len(val_cold_start_products),
        )

    if test_cold_start_users or test_cold_start_products:
        logger.warning(
            "Cold start in test set",
            cold_start_users=len(test_cold_start_users),
            cold_start_products=len(test_cold_start_products),
        )

    is_valid = len(val_cold_start_users) == 0 and len(val_cold_start_products) == 0
    return is_valid

