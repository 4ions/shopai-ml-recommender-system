import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from datetime import datetime

from src.data.ingestion import load_from_local
from src.data.splitting import temporal_split
from src.data.catalog import UserCatalog, ProductCatalog
from src.models.collaborative import CollaborativeFilter
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("Starting model retraining pipeline")

    logger.info("Loading latest processed data")
    df = load_from_local("data/processed/ratings.parquet")

    logger.info("Splitting data")
    train_df, val_df, test_df = temporal_split(df)

    logger.info("Creating/updating catalogs")
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

    version = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifacts_dir = "data/artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)

    logger.info("Saving updated catalogs", version=version)
    user_catalog.save(f"{artifacts_dir}/user_catalog_{version}.json")
    product_catalog.save(f"{artifacts_dir}/product_catalog_{version}.json")

    logger.info("Training new collaborative filter", version=version)
    collaborative_model = CollaborativeFilter(factors=50, iterations=15, regularization=0.1)
    collaborative_model.fit(train_df)

    model_path = f"{artifacts_dir}/collaborative_model_{version}.pkl"
    logger.info("Saving new model", path=model_path)
    collaborative_model.save(model_path)

    logger.info("Creating symlink to latest model")
    latest_path = f"{artifacts_dir}/collaborative_model.pkl"
    if os.path.exists(latest_path):
        os.remove(latest_path)
    os.symlink(os.path.basename(model_path), latest_path)

    logger.info("Model retraining pipeline completed", version=version, model_path=model_path)


if __name__ == "__main__":
    main()

