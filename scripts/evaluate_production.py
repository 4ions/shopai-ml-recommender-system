import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from src.data.ingestion import load_from_local
from src.data.splitting import temporal_split
from src.data.catalog import UserCatalog, ProductCatalog
from src.models.collaborative import CollaborativeFilter
from src.models.hybrid import HybridRecommender
from src.models.evaluation import RecommenderEvaluator
from src.monitoring.drift_detection import DriftDetector
from src.services.vector_store import FAISSVectorStore
from src.infrastructure.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("Starting production evaluation pipeline")

    logger.info("Loading data")
    df = load_from_local("data/processed/ratings.parquet")
    train_df, val_df, test_df = temporal_split(df)

    logger.info("Loading models")
    user_catalog = UserCatalog.load("data/artifacts/user_catalog.json")
    product_catalog = ProductCatalog.load("data/artifacts/product_catalog.json")
    collaborative_model = CollaborativeFilter.load("data/artifacts/collaborative_model.pkl")

    import glob
    index_files = glob.glob("data/artifacts/faiss_index_*.pkl")
    if not index_files:
        logger.error("No FAISS index found")
        return
    latest_index = max(index_files)
    vector_store = FAISSVectorStore.load(latest_index)

    hybrid_recommender = HybridRecommender(
        collaborative_model=collaborative_model,
        vector_store=vector_store,
        alpha=0.5,
    )

    logger.info("Running drift detection")
    drift_detector = DriftDetector(train_df)
    drift_results = drift_detector.detect_all_drift(test_df)

    logger.info("Evaluating model performance")
    evaluator = RecommenderEvaluator(test_df)

    def hybrid_recommend(user_id: str, top_k: int):
        return hybrid_recommender.recommend(user_id, top_k=top_k)

    evaluation_results = evaluator.evaluate(hybrid_recommend, k_values=[5, 10, 20])

    report = {
        "timestamp": datetime.now().isoformat(),
        "drift_detection": drift_results,
        "evaluation_metrics": evaluation_results,
        "recommendations": {
            "retrain_model": drift_results.get("overall_drift_detected", False),
            "refresh_embeddings": len(drift_results.get("popularity_drift", {}).get("current_top_n", [])) > 0,
        },
    }

    os.makedirs("data/reports", exist_ok=True)
    report_file = f"data/reports/production_evaluation_{datetime.now().strftime('%Y%m%d')}.json"
    
    logger.info("Saving production evaluation report", file=report_file)
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Production evaluation completed", report=report)

    if report["recommendations"]["retrain_model"]:
        logger.warning("DRIFT DETECTED: Consider retraining the model", drift_results=drift_results)
        logger.info("Run 'make retrain' to retrain the model")

    if report["recommendations"]["refresh_embeddings"]:
        logger.info("New products detected: Consider refreshing embeddings")
        logger.info("Run 'make refresh-embeddings' to update embeddings")


if __name__ == "__main__":
    main()

