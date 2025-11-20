import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from src.data.ingestion import load_from_local
from src.data.splitting import temporal_split
from src.data.catalog import UserCatalog, ProductCatalog
from src.models.baseline import PopularityBaseline, UserPopularityBaseline
from src.models.collaborative import CollaborativeFilter
from src.models.hybrid import HybridRecommender
from src.models.evaluation import RecommenderEvaluator
from src.services.vector_store import FAISSVectorStore
from src.config.settings import settings
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("Starting evaluation pipeline")

    logger.info("Loading data")
    df = load_from_local("data/processed/ratings.parquet")
    train_df, val_df, test_df = temporal_split(df)

    logger.info("Loading models and catalogs")
    user_catalog = UserCatalog.load("data/artifacts/user_catalog.json")
    product_catalog = ProductCatalog.load("data/artifacts/product_catalog.json")
    collaborative_model = CollaborativeFilter.load("data/artifacts/collaborative_model.pkl")

    import glob
    index_files = glob.glob("data/artifacts/faiss_index_*.pkl")
    if index_files:
        latest_index = max(index_files)
        vector_store = FAISSVectorStore.load(latest_index)
    else:
        logger.error("No FAISS index found")
        return

    hybrid_recommender = HybridRecommender(
        collaborative_model=collaborative_model,
        vector_store=vector_store,
        alpha=0.5,
    )

    logger.info("Evaluating models")

    evaluator = RecommenderEvaluator(test_df)

    results = {}

    logger.info("Evaluating popularity baseline")
    popularity_baseline = PopularityBaseline(train_df)

    def popularity_recommend(user_id: str, top_k: int):
        return popularity_baseline.recommend(top_k=top_k)

    results["popularity"] = evaluator.evaluate(popularity_recommend, k_values=[5, 10, 20])

    logger.info("Evaluating collaborative filter")

    def collaborative_recommend(user_id: str, top_k: int):
        return collaborative_model.recommend(user_id, top_k=top_k)

    results["collaborative"] = evaluator.evaluate(collaborative_recommend, k_values=[5, 10, 20])

    logger.info("Evaluating hybrid recommender")

    def hybrid_recommend(user_id: str, top_k: int):
        return hybrid_recommender.recommend(user_id, top_k=top_k)

    results["hybrid"] = evaluator.evaluate(hybrid_recommend, k_values=[5, 10, 20])

    logger.info("Saving evaluation results")
    os.makedirs("data/reports", exist_ok=True)
    with open("data/reports/evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    logger.info("Evaluation pipeline completed", results=results)


if __name__ == "__main__":
    main()

