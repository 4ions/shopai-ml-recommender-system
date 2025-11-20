import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from src.data.ingestion import load_from_local
from src.data.splitting import temporal_split, validate_split
from src.data.catalog import UserCatalog, ProductCatalog
from src.models.collaborative import CollaborativeFilter
from src.models.hybrid import HybridRecommender
from src.services.vector_store import FAISSVectorStore
from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("Starting training pipeline")

    logger.info("Loading processed data")
    df = load_from_local("data/processed/ratings.parquet")

    logger.info("Splitting data")
    train_df, val_df, test_df = temporal_split(df)
    is_valid = validate_split(train_df, val_df, test_df)
    logger.info("Split validation", is_valid=is_valid)

    logger.info("Creating catalogs")
    user_catalog = UserCatalog(train_df)
    
    products_file = "products_catalog.csv"
    if os.path.exists(products_file):
        products_df = pd.read_csv(products_file)
    else:
        logger.warning("Products catalog not found, creating from transactions")
        unique_products = train_df["product_id"].unique()
        products_df = pd.DataFrame({
            "product_id": unique_products,
            "category": ["unknown"] * len(unique_products),
            "name": unique_products,
            "description": ["Product description"] * len(unique_products),
        })
    
    product_catalog = ProductCatalog(train_df, products_df)

    logger.info("Saving catalogs")
    os.makedirs("data/artifacts", exist_ok=True)
    user_catalog.save("data/artifacts/user_catalog.json")
    product_catalog.save("data/artifacts/product_catalog.json")

    logger.info("Training collaborative filter")
    collaborative_model = CollaborativeFilter(factors=50, iterations=15, regularization=0.1)
    collaborative_model.fit(train_df)

    logger.info("Saving collaborative model")
    collaborative_model.save("data/artifacts/collaborative_model.pkl")

    logger.info("Loading vector store")
    import glob
    index_files = glob.glob("data/artifacts/faiss_index_*.pkl")
    if index_files:
        latest_index = max(index_files)
        vector_store = FAISSVectorStore.load(latest_index)
    else:
        logger.warning("No FAISS index found, creating empty store")
        vector_store = FAISSVectorStore(
            dimension=settings.openai_embedding_dimension,
            index_type=settings.faiss_index_type,
        )

    logger.info("Creating hybrid recommender")
    hybrid_recommender = HybridRecommender(
        collaborative_model=collaborative_model,
        vector_store=vector_store,
        alpha=0.5,
        fusion_strategy="weighted_sum",
    )

    logger.info("Training pipeline completed")


if __name__ == "__main__":
    main()

