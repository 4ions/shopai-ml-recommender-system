from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import pandas as pd

from src.config.constants import RATING_MIN, RATING_MAX
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class Transaction(BaseModel):
    user_id: str
    product_id: str
    rating: int = Field(ge=RATING_MIN, le=RATING_MAX)
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")


class Product(BaseModel):
    product_id: str
    category: str
    name: str
    description: str


def validate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Validating transactions", total_rows=len(df))
    
    errors = []
    valid_rows = []

    for idx, row in df.iterrows():
        try:
            Transaction(
                user_id=str(row["user_id"]),
                product_id=str(row["product_id"]),
                rating=int(row["rating"]),
                timestamp=str(row["timestamp"]),
            )
            valid_rows.append(idx)
        except Exception as e:
            errors.append({"row": idx, "error": str(e)})

    if errors:
        logger.warning("Validation errors found", error_count=len(errors), sample_errors=errors[:5])

    validated_df = df.loc[valid_rows].copy()
    logger.info("Validation complete", valid_rows=len(validated_df), invalid_rows=len(errors))
    
    return validated_df


def validate_products(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Validating products", total_rows=len(df))
    
    errors = []
    valid_rows = []

    for idx, row in df.iterrows():
        try:
            Product(
                product_id=str(row["product_id"]),
                category=str(row["category"]),
                name=str(row["name"]),
                description=str(row["description"]),
            )
            valid_rows.append(idx)
        except Exception as e:
            errors.append({"row": idx, "error": str(e)})

    if errors:
        logger.warning("Validation errors found", error_count=len(errors), sample_errors=errors[:5])

    validated_df = df.loc[valid_rows].copy()
    logger.info("Validation complete", valid_rows=len(validated_df), invalid_rows=len(errors))
    
    return validated_df


def get_data_quality_report(df: pd.DataFrame, data_type: str = "transactions") -> Dict[str, Any]:
    report = {
        "total_rows": len(df),
        "missing_values": df.isnull().sum().to_dict(),
        "duplicates": df.duplicated().sum(),
    }

    if data_type == "transactions":
        report["rating_distribution"] = df["rating"].value_counts().to_dict()
        report["rating_stats"] = {
            "mean": float(df["rating"].mean()),
            "std": float(df["rating"].std()),
            "min": int(df["rating"].min()),
            "max": int(df["rating"].max()),
        }
        report["unique_users"] = df["user_id"].nunique()
        report["unique_products"] = df["product_id"].nunique()
        report["sparsity"] = 1 - (len(df) / (report["unique_users"] * report["unique_products"]))

    return report

