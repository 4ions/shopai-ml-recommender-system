import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import numpy as np
from datetime import datetime

from src.data.ingestion import load_from_local
from src.models.embeddings import generate_embeddings, save_embeddings, load_embeddings
from src.services.vector_store import FAISSVectorStore
from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("Starting embeddings refresh pipeline")

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
        products_df = pd.read_csv(products_file)

    logger.info("Checking for new products")
    artifacts_dir = "data/artifacts"
    import glob
    embedding_files = glob.glob(f"{artifacts_dir}/embeddings_*.npy")
    
    if embedding_files:
        latest_embeddings_file = max(embedding_files)
        logger.info("Loading existing embeddings", file=latest_embeddings_file)
        existing_embeddings = load_embeddings(latest_embeddings_file)
        
        metadata_file = latest_embeddings_file.replace(".npy", "_metadata.json")
        if os.path.exists(metadata_file):
            import json
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            existing_product_ids = set(metadata.get("product_ids", []))
        else:
            existing_product_ids = set()
    else:
        existing_embeddings = None
        existing_product_ids = set()

    all_product_ids = set(products_df["product_id"].unique())
    new_product_ids = all_product_ids - existing_product_ids

    if not new_product_ids:
        logger.info("No new products found, embeddings are up to date")
        return

    logger.info("Found new products", count=len(new_product_ids))
    new_products = products_df[products_df["product_id"].isin(new_product_ids)].to_dict("records")

    logger.info("Generating embeddings for new products", count=len(new_products))
    new_embeddings = generate_embeddings(new_products, batch_size=100)

    if existing_embeddings is not None:
        logger.info("Combining with existing embeddings")
        all_embeddings = np.vstack([existing_embeddings, new_embeddings])
        all_product_ids_list = list(existing_product_ids) + list(new_product_ids)
    else:
        all_embeddings = new_embeddings
        all_product_ids_list = list(new_product_ids)

    version = datetime.now().strftime("%Y%m%d")
    embeddings_file = f"{artifacts_dir}/embeddings_{version}.npy"
    
    metadata = {
        "model_id": settings.openai_model_id,
        "dimension": settings.openai_embedding_dimension,
        "date": version,
        "product_count": len(all_product_ids_list),
        "product_ids": all_product_ids_list,
    }

    logger.info("Saving updated embeddings", file=embeddings_file)
    os.makedirs(artifacts_dir, exist_ok=True)
    save_embeddings(all_embeddings, embeddings_file, metadata=metadata)

    logger.info("Updating FAISS index")
    vector_store = FAISSVectorStore(
        dimension=settings.openai_embedding_dimension,
        index_type=settings.faiss_index_type,
    )
    vector_store.add_embeddings(all_product_ids_list, all_embeddings)

    index_file = f"{artifacts_dir}/faiss_index_{version}.pkl"
    logger.info("Saving updated FAISS index", file=index_file)
    vector_store.save(index_file)

    logger.info("Embeddings refresh pipeline completed", new_products=len(new_product_ids))


if __name__ == "__main__":
    main()

