"""Unit tests for vector store."""
import pytest
import numpy as np
import tempfile
import os

from src.services.vector_store import FAISSVectorStore
from src.config.constants import FAISSIndexType


def test_vector_store_creation():
    """Test creating a vector store."""
    store = FAISSVectorStore(dimension=1536, index_type=FAISSIndexType.INNER_PRODUCT)
    assert store.dimension == 1536
    assert store.index_type == FAISSIndexType.INNER_PRODUCT
    assert store.index is None
    assert len(store.product_ids) == 0


def test_add_embeddings():
    """Test adding embeddings to vector store."""
    store = FAISSVectorStore(dimension=1536, index_type=FAISSIndexType.INNER_PRODUCT)
    
    product_ids = ["P001", "P002", "P003"]
    embeddings = np.random.rand(3, 1536).astype(np.float32)
    
    store.add_embeddings(product_ids, embeddings)
    
    assert len(store.product_ids) == 3
    assert store.product_ids == product_ids
    assert store.index is not None


def test_search():
    """Test searching in vector store."""
    store = FAISSVectorStore(dimension=1536, index_type=FAISSIndexType.INNER_PRODUCT)
    
    product_ids = ["P001", "P002", "P003"]
    embeddings = np.random.rand(3, 1536).astype(np.float32)
    store.add_embeddings(product_ids, embeddings)
    
    query_embedding = np.random.rand(1536).astype(np.float32)
    results = store.search(query_embedding, top_k=2)
    
    assert len(results) <= 2
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    assert all(r[0] in product_ids for r in results)


def test_search_empty_store():
    """Test searching in empty vector store."""
    store = FAISSVectorStore(dimension=1536, index_type=FAISSIndexType.INNER_PRODUCT)
    
    query_embedding = np.random.rand(1536).astype(np.float32)
    results = store.search(query_embedding, top_k=5)
    
    assert results == []


def test_save_and_load():
    """Test saving and loading vector store."""
    store = FAISSVectorStore(dimension=1536, index_type=FAISSIndexType.INNER_PRODUCT)
    
    product_ids = ["P001", "P002"]
    embeddings = np.random.rand(2, 1536).astype(np.float32)
    store.add_embeddings(product_ids, embeddings)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
        temp_path = f.name
    
    try:
        store.save(temp_path)
        assert os.path.exists(temp_path)
        
        loaded_store = FAISSVectorStore.load(temp_path)
        assert loaded_store.dimension == 1536
        assert loaded_store.product_ids == product_ids
        assert loaded_store.index is not None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_embedding():
    """Test getting embedding for a product."""
    store = FAISSVectorStore(dimension=1536, index_type=FAISSIndexType.INNER_PRODUCT)
    
    product_ids = ["P001", "P002"]
    embeddings = np.random.rand(2, 1536).astype(np.float32)
    store.add_embeddings(product_ids, embeddings)
    
    embedding = store.get_embedding("P001")
    assert embedding is not None
    assert embedding.shape == (1536,)
    
    missing_embedding = store.get_embedding("P999")
    assert missing_embedding is None

