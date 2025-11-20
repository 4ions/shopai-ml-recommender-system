from typing import List, Tuple, Optional, Dict
import numpy as np
import faiss
import pickle

from src.config.settings import settings
from src.config.constants import FAISSIndexType
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class FAISSVectorStore:
    """FAISS-based vector store for efficient similarity search.
    
    This class provides a wrapper around FAISS indices for storing and searching
    product embeddings. Supports both L2 distance and inner product similarity.
    
    Attributes:
        dimension: Dimension of embedding vectors
        index_type: Type of FAISS index ("L2" or "InnerProduct")
        index: FAISS index instance
        product_ids: List of product IDs in the same order as vectors in the index
        embeddings_map: Dictionary mapping product_id to embedding vector
    """
    
    def __init__(self, dimension: int, index_type: str = "InnerProduct"):
        """Initialize FAISS vector store.
        
        Args:
            dimension: Dimension of embedding vectors (e.g., 1536 for text-embedding-3-large)
            index_type: Type of similarity metric. "InnerProduct" for cosine similarity
                (after L2 normalization) or "L2" for Euclidean distance.
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index: Optional[faiss.Index] = None
        self.product_ids: List[str] = []
        self.embeddings_map: Dict[str, np.ndarray] = {}

    def _create_index(self) -> faiss.Index:
        if self.index_type == FAISSIndexType.L2:
            index = faiss.IndexFlatL2(self.dimension)
        elif self.index_type == FAISSIndexType.INNER_PRODUCT:
            index = faiss.IndexFlatIP(self.dimension)
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

        return index

    def add_embeddings(self, product_ids: List[str], embeddings: np.ndarray) -> None:
        """Add embeddings to the vector store.
        
        Adds product embeddings to the FAISS index. If index doesn't exist, creates it.
        For InnerProduct index type, normalizes embeddings to unit length.
        
        Args:
            product_ids: List of product IDs corresponding to each embedding
            embeddings: NumPy array of shape (n_products, dimension) containing embeddings
        
        Raises:
            ValueError: If embedding dimension doesn't match store dimension
        
        Example:
            >>> store = FAISSVectorStore(dimension=1536)
            >>> product_ids = ["P001", "P002"]
            >>> embeddings = np.random.rand(2, 1536).astype(np.float32)
            >>> store.add_embeddings(product_ids, embeddings)
        """
        logger.info("Adding embeddings to vector store", count=len(product_ids), shape=embeddings.shape)

        actual_dimension = embeddings.shape[1]
        if actual_dimension != self.dimension:
            logger.warning(
                "Embedding dimension mismatch, updating dimension",
                expected=self.dimension,
                actual=actual_dimension,
            )
            self.dimension = actual_dimension

        if self.index is None:
            self.index = self._create_index()

        if self.index_type == FAISSIndexType.INNER_PRODUCT:
            faiss.normalize_L2(embeddings)

        self.index.add(embeddings.astype(np.float32))
        self.product_ids.extend(product_ids)

        for product_id, embedding in zip(product_ids, embeddings):
            self.embeddings_map[product_id] = embedding

        try:
            total_vectors = self.index.ntotal if hasattr(self.index, 'ntotal') else len(self.product_ids)
        except (AttributeError, TypeError):
            total_vectors = len(self.product_ids)
        logger.info("Embeddings added", total_vectors=total_vectors)

    def search(
        self, query_embedding: np.ndarray, top_k: int = 10, threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """Search for similar products using a query embedding.
        
        Performs similarity search in the FAISS index and returns top-k most similar products.
        
        Args:
            query_embedding: Query embedding vector of shape (dimension,) or (1, dimension)
            top_k: Number of top results to return
            threshold: Optional similarity threshold. For InnerProduct, filters results below threshold.
                For L2, filters results above threshold.
        
        Returns:
            List of tuples (product_id, similarity_score) sorted by similarity (descending).
            Returns empty list if index is empty.
        
        Raises:
            ValueError: If query embedding dimension doesn't match store dimension
        
        Example:
            >>> store = FAISSVectorStore(dimension=1536)
            >>> query = np.random.rand(1536).astype(np.float32)
            >>> results = store.search(query, top_k=5)
            >>> len(results)
            5
        """
        try:
            index_size = self.index.ntotal if hasattr(self.index, 'ntotal') else len(self.product_ids)
        except (AttributeError, TypeError):
            index_size = len(self.product_ids)
        
        if self.index is None or index_size == 0:
            logger.warning("Index is empty")
            return []

        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        if query_embedding.shape[1] != self.dimension:
            raise ValueError(
                f"Query dimension mismatch: expected {self.dimension}, got {query_embedding.shape[1]}"
            )

        if self.index_type == FAISSIndexType.INNER_PRODUCT:
            faiss.normalize_L2(query_embedding)

        query_embedding = query_embedding.astype(np.float32)

        try:
            max_k = self.index.ntotal if hasattr(self.index, 'ntotal') else len(self.product_ids)
        except (AttributeError, TypeError):
            max_k = len(self.product_ids)
        distances, indices = self.index.search(query_embedding, min(top_k, max_k))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue

            if threshold is not None:
                if self.index_type == FAISSIndexType.L2 and dist > threshold:
                    continue
                if self.index_type == FAISSIndexType.INNER_PRODUCT and dist < threshold:
                    continue

            product_id = self.product_ids[idx]
            score = float(dist)
            results.append((product_id, score))

        return results

    def search_by_vector(
        self, query_embedding: np.ndarray, top_k: int = 10
    ) -> List[Tuple[str, float]]:
        return self.search(query_embedding, top_k=top_k)

    def get_embedding(self, product_id: str) -> Optional[np.ndarray]:
        return self.embeddings_map.get(product_id)

    def get_popular_items(self, top_k: int = 10) -> List[Tuple[str, float]]:
        if not self.product_ids:
            return []

        return [(product_id, 1.0) for product_id in self.product_ids[:top_k]]

    def distance(self, product_id1: str, product_id2: str) -> float:
        emb1 = self.get_embedding(product_id1)
        emb2 = self.get_embedding(product_id2)

        if emb1 is None or emb2 is None:
            return 1.0

        if self.index_type == FAISSIndexType.INNER_PRODUCT:
            return 1.0 - np.dot(emb1, emb2)
        else:
            return np.linalg.norm(emb1 - emb2)

    def save(self, file_path: str) -> None:
        logger.info("Saving vector store", file_path=file_path)
        if self.index is None:
            raise ValueError("Index is empty")

        data = {
            "index": self.index,
            "product_ids": self.product_ids,
            "embeddings_map": self.embeddings_map,
            "dimension": self.dimension,
            "index_type": self.index_type,
        }

        with open(file_path, "wb") as f:
            pickle.dump(data, f)

        logger.info("Vector store saved")

    @classmethod
    def load(cls, file_path: str) -> "FAISSVectorStore":
        logger.info("Loading vector store", file_path=file_path)

        with open(file_path, "rb") as f:
            data = pickle.load(f)

        logger.info(
            "Loaded pickle data",
            keys=list(data.keys()),
            product_ids_count=len(data.get("product_ids", [])),
            has_index="index" in data,
        )

        instance = cls(dimension=data["dimension"], index_type=data["index_type"])
        instance.index = data["index"]
        instance.product_ids = data.get("product_ids", [])
        instance.embeddings_map = data.get("embeddings_map", {})
        
        logger.info(
            "Assigned to instance",
            product_ids_count=len(instance.product_ids),
            embeddings_map_count=len(instance.embeddings_map),
        )

        try:
            if hasattr(instance.index, 'ntotal'):
                total_vectors = instance.index.ntotal
            else:
                total_vectors = len(instance.product_ids) if instance.product_ids else 0
        except (AttributeError, TypeError) as e:
            logger.warning("Could not get ntotal from index, using product_ids count", error=str(e))
            total_vectors = len(instance.product_ids) if instance.product_ids else 0
        
        logger.info(
            "Vector store loaded",
            total_vectors=total_vectors,
            product_ids_count=len(instance.product_ids) if instance.product_ids else 0,
            has_index=instance.index is not None
        )
        return instance

