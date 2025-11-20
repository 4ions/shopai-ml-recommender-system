import pytest
import pandas as pd
from src.data.validation import Transaction, Product, validate_transactions, validate_products


def test_transaction_validation():
    valid_transaction = Transaction(
        user_id="U001",
        product_id="P001",
        rating=5,
        timestamp="2024-01-01T12:00:00",
    )
    assert valid_transaction.user_id == "U001"
    assert valid_transaction.rating == 5


def test_transaction_invalid_rating():
    with pytest.raises(Exception):
        Transaction(
            user_id="U001",
            product_id="P001",
            rating=6,
            timestamp="2024-01-01T12:00:00",
        )


def test_validate_transactions_dataframe():
    df = pd.DataFrame({
        "user_id": ["U001", "U002"],
        "product_id": ["P001", "P002"],
        "rating": [5, 4],
        "timestamp": ["2024-01-01T12:00:00", "2024-01-02T12:00:00"],
    })
    
    validated_df = validate_transactions(df)
    assert len(validated_df) == 2


def test_product_validation():
    valid_product = Product(
        product_id="P001",
        category="electronics",
        name="Product 1",
        description="Description",
    )
    assert valid_product.product_id == "P001"
    assert valid_product.category == "electronics"

