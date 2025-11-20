from typing import Dict, Tuple
import pandas as pd
from datetime import datetime
import pytz

from src.config.constants import RATING_MIN, RATING_MAX
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def normalize_timestamps(df: pd.DataFrame, timezone: str = "UTC") -> pd.DataFrame:
    logger.info("Normalizing timestamps", timezone=timezone)

    tz = pytz.timezone(timezone)
    df = df.copy()

    def parse_timestamp(ts: str) -> datetime:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            return dt.astimezone(tz)
        except Exception as e:
            logger.warning("Error parsing timestamp", timestamp=ts, error=str(e))
            return None

    df["timestamp"] = df["timestamp"].apply(parse_timestamp)
    df = df.dropna(subset=["timestamp"])
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    logger.info("Timestamps normalized", valid_timestamps=len(df))
    return df


def remove_duplicates(df: pd.DataFrame, strategy: str = "keep_last") -> pd.DataFrame:
    logger.info("Removing duplicates", strategy=strategy, initial_rows=len(df))

    if strategy == "keep_last":
        df = df.drop_duplicates(subset=["user_id", "product_id", "timestamp"], keep="last")
    elif strategy == "keep_first":
        df = df.drop_duplicates(subset=["user_id", "product_id", "timestamp"], keep="first")
    else:
        df = df.drop_duplicates(subset=["user_id", "product_id", "timestamp"])

    logger.info("Duplicates removed", final_rows=len(df))
    return df


def filter_valid_ratings(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Filtering valid ratings", initial_rows=len(df))

    initial_count = len(df)
    df = df[(df["rating"] >= RATING_MIN) & (df["rating"] <= RATING_MAX)].copy()

    filtered_count = initial_count - len(df)
    if filtered_count > 0:
        logger.warning("Filtered invalid ratings", filtered_count=filtered_count)

    logger.info("Valid ratings filtered", final_rows=len(df))
    return df


def encode_ids(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Dict[str, int]]]:
    logger.info("Encoding user and product IDs")

    user_ids = df["user_id"].unique()
    product_ids = df["product_id"].unique()

    user_to_idx = {user_id: idx for idx, user_id in enumerate(user_ids)}
    idx_to_user = {idx: user_id for user_id, idx in user_to_idx.items()}

    product_to_idx = {product_id: idx for idx, product_id in enumerate(product_ids)}
    idx_to_product = {idx: product_id for product_id, idx in product_to_idx.items()}

    df = df.copy()
    df["user_idx"] = df["user_id"].map(user_to_idx)
    df["product_idx"] = df["product_id"].map(product_to_idx)

    mappings = {
        "user_to_idx": user_to_idx,
        "idx_to_user": idx_to_user,
        "product_to_idx": product_to_idx,
        "idx_to_product": idx_to_product,
    }

    logger.info("IDs encoded", unique_users=len(user_ids), unique_products=len(product_ids))
    return df, mappings


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Starting data cleaning", initial_rows=len(df))

    df = normalize_timestamps(df)
    df = remove_duplicates(df)
    df = filter_valid_ratings(df)

    logger.info("Data cleaning complete", final_rows=len(df))
    return df

