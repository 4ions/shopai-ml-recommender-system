import pytest
import pandas as pd
from src.data.splitting import temporal_split, validate_split


def test_temporal_split():
    df = pd.DataFrame({
        "user_id": ["U001"] * 100,
        "product_id": [f"P{i:03d}" for i in range(100)],
        "rating": [4] * 100,
        "timestamp": pd.date_range("2024-01-01", periods=100, freq="D"),
    })
    
    train_df, val_df, test_df = temporal_split(df)
    
    assert len(train_df) == 70
    assert len(val_df) == 15
    assert len(test_df) == 15
    
    assert train_df["timestamp"].max() <= val_df["timestamp"].min()
    assert val_df["timestamp"].max() <= test_df["timestamp"].min()


def test_validate_split():
    train_df = pd.DataFrame({
        "user_id": ["U001", "U002"],
        "product_id": ["P001", "P002"],
    })
    
    val_df = pd.DataFrame({
        "user_id": ["U001"],
        "product_id": ["P001"],
    })
    
    test_df = pd.DataFrame({
        "user_id": ["U002"],
        "product_id": ["P002"],
    })
    
    is_valid = validate_split(train_df, val_df, test_df)
    assert is_valid is True

