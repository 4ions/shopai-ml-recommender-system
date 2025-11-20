"""Unit tests for embeddings module."""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.models.embeddings import prepare_product_text, get_embedding, generate_embeddings


def test_prepare_product_text_full():
    """Test prepare_product_text with all fields."""
    product = {
        "name": "Test Product",
        "description": "Test Description",
        "category": "Electronics"
    }
    text = prepare_product_text(product)
    assert "Test Product" in text
    assert "Test Description" in text
    assert "Category: Electronics" in text


def test_prepare_product_text_minimal():
    """Test prepare_product_text with minimal fields."""
    product = {"name": "Test Product"}
    text = prepare_product_text(product)
    assert text == "Test Product"


def test_prepare_product_text_empty():
    """Test prepare_product_text with empty product."""
    product = {}
    text = prepare_product_text(product)
    assert text == "Product"


@patch("src.models.embeddings.OpenAI")
def test_get_embedding_success(mock_openai):
    """Test successful embedding retrieval."""
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.embeddings.create.return_value = Mock(
        data=[Mock(embedding=[0.1, 0.2, 0.3] * 512)]
    )
    
    from src.models.embeddings import get_embedding
    from src.config.settings import settings
    
    with patch("src.models.embeddings.settings", settings):
        embedding = get_embedding(mock_client, "test text")
        assert len(embedding) == 1536
        assert isinstance(embedding, list)


@patch("src.models.embeddings.OpenAI")
def test_generate_embeddings_batch(mock_openai):
    """Test batch embedding generation."""
    mock_client = Mock()
    mock_openai.return_value = mock_client
    
    # Mock embedding response
    mock_embedding = [0.1] * 1536
    mock_client.embeddings.create.return_value = Mock(
        data=[Mock(embedding=mock_embedding)]
    )
    
    products = [
        {"product_id": "P001", "name": "Product 1", "description": "Desc 1"},
        {"product_id": "P002", "name": "Product 2", "description": "Desc 2"},
    ]
    
    with patch("src.models.embeddings.settings") as mock_settings:
        mock_settings.openai_model_id = "text-embedding-3-large"
        mock_settings.openai_embedding_dimension = 1536
        mock_settings.openai_api_key = "test-key"
        
        embeddings = generate_embeddings(products, batch_size=2, client=mock_client)
        
        assert embeddings.shape[0] == 2
        assert embeddings.shape[1] == 1536
        assert isinstance(embeddings, np.ndarray)

