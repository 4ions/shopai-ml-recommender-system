from typing import List, Dict, Optional
import numpy as np
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from src.config.settings import settings
from src.infrastructure.logging import get_logger
from src.infrastructure.metrics import openai_api_calls_total

logger = get_logger(__name__)


def prepare_product_text(product: Dict[str, str]) -> str:
    """Prepare product text for embedding generation.
    
    Combines product name, description, and category into a single text string
    suitable for embedding generation.
    
    Args:
        product: Dictionary containing product information with keys:
            - name: Product name
            - description: Product description (optional)
            - category: Product category (optional)
    
    Returns:
        Combined text string. Returns "Product" if all fields are empty.
    
    Example:
        >>> product = {"name": "Laptop", "description": "Gaming laptop", "category": "Electronics"}
        >>> prepare_product_text(product)
        "Laptop Gaming laptop Category: Electronics"
    """
    name = product.get("name", "")
    description = product.get("description", "")
    category = product.get("category", "")

    text_parts = [name]
    if description:
        text_parts.append(description)
    if category:
        text_parts.append(f"Category: {category}")

    text = " ".join(text_parts).strip()
    if not text:
        text = "Product"

    return text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_embedding(client: OpenAI, text: str) -> List[float]:
    """Get embedding vector for a text using OpenAI API.
    
    Makes a call to OpenAI embeddings API with retry logic and error handling.
    Updates Prometheus metrics for monitoring.
    
    Args:
        client: OpenAI client instance
        text: Text to generate embedding for
    
    Returns:
        List of floats representing the embedding vector
    
    Raises:
        Exception: If embedding generation fails after retries
    
    Example:
        >>> client = OpenAI(api_key="...")
        >>> embedding = get_embedding(client, "laptop computer")
        >>> len(embedding)
        1536
    """
    try:
        response = client.embeddings.create(
            model=settings.openai_model_id,
            input=text,
            dimensions=settings.openai_embedding_dimension,
        )
        openai_api_calls_total.labels(operation="embedding", status="success").inc()
        return response.data[0].embedding
    except Exception as e:
        openai_api_calls_total.labels(operation="embedding", status="error").inc()
        logger.error("Error getting embedding", error=str(e))
        raise


def generate_embeddings(
    products: List[Dict[str, str]],
    batch_size: int = 100,
    client: Optional[OpenAI] = None,
) -> np.ndarray:
    """Generate embeddings for a list of products in batches.
    
    Processes products in batches to optimize API usage and handle rate limits.
    Uses progress bar to show generation progress.
    
    Args:
        products: List of product dictionaries, each containing:
            - product_id: Unique product identifier
            - name: Product name
            - description: Product description (optional)
            - category: Product category (optional)
        batch_size: Number of products to process per batch. Defaults to 100.
        client: Optional OpenAI client. If None, creates a new client.
    
    Returns:
        NumPy array of shape (n_products, embedding_dimension) containing
        all product embeddings. Failed embeddings are replaced with zero vectors.
    
    Example:
        >>> products = [
        ...     {"product_id": "P001", "name": "Laptop", "description": "Gaming laptop"},
        ...     {"product_id": "P002", "name": "Mouse", "description": "Wireless mouse"}
        ... ]
        >>> embeddings = generate_embeddings(products, batch_size=2)
        >>> embeddings.shape
        (2, 1536)
    """
    logger.info("Generating embeddings", total_products=len(products), batch_size=batch_size)

    if client is None:
        client = OpenAI(api_key=settings.openai_api_key)

    embeddings = []
    product_texts = [prepare_product_text(product) for product in products]

    for i in tqdm(range(0, len(product_texts), batch_size), desc="Generating embeddings"):
        batch_texts = product_texts[i : i + batch_size]
        batch_embeddings = []

        for text in batch_texts:
            try:
                embedding = get_embedding(client, text)
                batch_embeddings.append(embedding)
            except Exception as e:
                logger.error("Failed to get embedding", text=text[:50], error=str(e))
                batch_embeddings.append([0.0] * settings.openai_embedding_dimension)

        embeddings.extend(batch_embeddings)

    embeddings_array = np.array(embeddings, dtype=np.float32)
    logger.info("Embeddings generated", shape=embeddings_array.shape)

    return embeddings_array


def save_embeddings(embeddings: np.ndarray, file_path: str, metadata: Optional[Dict] = None) -> None:
    """Save embeddings to disk in NumPy format.
    
    Saves embeddings array as .npy file and optionally saves metadata as JSON.
    
    Args:
        embeddings: NumPy array of embeddings with shape (n_samples, dimension)
        file_path: Path to save the .npy file
        metadata: Optional dictionary with metadata (e.g., model_id, date, product_ids).
            If provided, saves to a .json file with the same base name.
    
    Example:
        >>> embeddings = np.random.rand(100, 1536).astype(np.float32)
        >>> metadata = {"model_id": "text-embedding-3-large", "date": "2024-01-15"}
        >>> save_embeddings(embeddings, "embeddings.npy", metadata)
    """
    logger.info("Saving embeddings", file_path=file_path, shape=embeddings.shape)

    np.save(file_path, embeddings)

    if metadata:
        import json
        metadata_path = file_path.replace(".npy", "_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    logger.info("Embeddings saved")


def load_embeddings(file_path: str) -> np.ndarray:
    """Load embeddings from disk.
    
    Args:
        file_path: Path to the .npy file containing embeddings
    
    Returns:
        NumPy array of embeddings with shape (n_samples, dimension)
    
    Example:
        >>> embeddings = load_embeddings("embeddings.npy")
        >>> embeddings.shape
        (100, 1536)
    """
    logger.info("Loading embeddings", file_path=file_path)
    embeddings = np.load(file_path)
    logger.info("Embeddings loaded", shape=embeddings.shape)
    return embeddings

