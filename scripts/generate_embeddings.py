import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import numpy as np

from src.data.ingestion import load_from_local
from src.models.embeddings import generate_embeddings, save_embeddings
from src.services.vector_store import FAISSVectorStore
from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("Starting embeddings generation pipeline")

    products_file = "products_catalog.csv"
    if not os.path.exists(products_file):
        logger.warning("Products catalog not found, creating from transactions")
        transactions_df = load_from_local("data/processed/ratings.parquet")
        unique_products = transactions_df["product_id"].unique()
        products_df = pd.DataFrame({
            "product_id": unique_products,
            "category": ["unknown"] * len(unique_products),
            "name": unique_products,
            "description": ["Product description"] * len(unique_products),
        })
    else:
        products_df = load_from_local(products_file)

    products = products_df.to_dict("records")

    logger.info("Generating embeddings", product_count=len(products))
    embeddings = generate_embeddings(products, batch_size=100)

    version = datetime.now().strftime("%Y%m%d")
    embeddings_file = f"data/artifacts/embeddings_{version}.npy"
    metadata = {
        "model_id": settings.openai_model_id,
        "dimension": settings.openai_embedding_dimension,
        "date": version,
        "product_count": len(products),
    }

    logger.info("Saving embeddings", file=embeddings_file)
    os.makedirs(os.path.dirname(embeddings_file), exist_ok=True)
    save_embeddings(embeddings, embeddings_file, metadata=metadata)

    logger.info("Creating FAISS index")
    vector_store = FAISSVectorStore(
        dimension=settings.openai_embedding_dimension,
        index_type=settings.faiss_index_type,
    )

    product_ids = [p["product_id"] for p in products]
    vector_store.add_embeddings(product_ids, embeddings)

    index_file = f"data/artifacts/faiss_index_{version}.pkl"
    logger.info("Saving FAISS index", file=index_file)
    vector_store.save(index_file)

    logger.info("Embeddings generation pipeline completed")


if __name__ == "__main__":
    main()

