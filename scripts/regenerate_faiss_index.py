import sys
import os
import glob
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from src.services.vector_store import FAISSVectorStore
from src.models.embeddings import load_embeddings
from src.data.ingestion import load_from_local
from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("Regenerating FAISS index for current architecture")

    # Find latest embeddings file
    embeddings_files = glob.glob("data/artifacts/embeddings_*.npy")
    if not embeddings_files:
        logger.error("No embeddings files found")
        return
    
    embeddings_file = max(embeddings_files)
    logger.info("Using embeddings file", file=embeddings_file)

    # Load embeddings
    logger.info("Loading embeddings", file=embeddings_file)
    embeddings = load_embeddings(embeddings_file)

    # Try to get product_ids from metadata or products catalog
    product_ids = None
    metadata_file = embeddings_file.replace(".npy", "_metadata.json")
    if os.path.exists(metadata_file):
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        product_ids = metadata.get("product_ids", [])
        logger.info("Found product_ids in metadata", count=len(product_ids))
    
    if not product_ids or len(product_ids) != len(embeddings):
        logger.info("Getting product_ids from products catalog or transactions")
        # Try products catalog
        products_file = "products_catalog.csv"
        if os.path.exists(products_file):
            products_df = load_from_local(products_file)
            product_ids = products_df["product_id"].tolist()
            logger.info("Found product_ids in products catalog", count=len(product_ids))
        else:
            # Fallback to transactions
            transactions_file = "data/processed/ratings.parquet"
            if os.path.exists(transactions_file):
                transactions_df = load_from_local(transactions_file)
                product_ids = sorted(transactions_df["product_id"].unique().tolist())
                logger.info("Found product_ids in transactions", count=len(product_ids))
    
    if not product_ids or len(product_ids) != len(embeddings):
        logger.warning(
            "Product IDs count mismatch, using first N products",
            embeddings_count=len(embeddings),
            product_ids_count=len(product_ids) if product_ids else 0
        )
        if product_ids and len(product_ids) > len(embeddings):
            product_ids = product_ids[:len(embeddings)]
        elif not product_ids or len(product_ids) < len(embeddings):
            # Generate placeholder IDs
            missing = len(embeddings) - (len(product_ids) if product_ids else 0)
            if not product_ids:
                product_ids = []
            product_ids.extend([f"P{i:03d}" for i in range(len(product_ids), len(product_ids) + missing)])

    logger.info("Creating new FAISS index", dimension=embeddings.shape[1], vectors=len(embeddings), product_ids=len(product_ids))
    vector_store = FAISSVectorStore(
        dimension=embeddings.shape[1],
        index_type=settings.faiss_index_type,
    )

    logger.info("Adding embeddings to index")
    vector_store.add_embeddings(product_ids, embeddings)

    # Use same version as embeddings file
    version = os.path.basename(embeddings_file).replace("embeddings_", "").replace(".npy", "")
    output_file = f"data/artifacts/faiss_index_{version}.pkl"
    logger.info("Saving index", file=output_file)
    vector_store.save(output_file)

    # Verify the saved index
    logger.info("Verifying saved index")
    loaded_store = FAISSVectorStore.load(output_file)
    try:
        total = loaded_store.index.ntotal if hasattr(loaded_store.index, 'ntotal') else len(loaded_store.product_ids)
    except:
        total = len(loaded_store.product_ids)
    logger.info("Index verified", total_vectors=total, product_ids_count=len(loaded_store.product_ids))

    logger.info("Index regenerated successfully", file=output_file)


if __name__ == "__main__":
    main()

