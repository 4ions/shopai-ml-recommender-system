from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from scipy import stats

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DriftDetector:
    def __init__(self, baseline_data: pd.DataFrame):
        self.baseline_data = baseline_data
        self.baseline_stats = self._compute_baseline_stats(baseline_data)

    def _compute_baseline_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        stats_dict = {
            "rating_distribution": df["rating"].value_counts().to_dict(),
            "rating_mean": float(df["rating"].mean()),
            "rating_std": float(df["rating"].std()),
            "unique_users": int(df["user_id"].nunique()),
            "unique_products": int(df["product_id"].nunique()),
            "total_interactions": int(len(df)),
            "top_products": df["product_id"].value_counts().head(20).to_dict(),
        }
        return stats_dict

    def detect_rating_drift(
        self, current_data: pd.DataFrame, threshold: float = 0.05
    ) -> Tuple[bool, Dict[str, Any]]:
        logger.info("Detecting rating distribution drift")

        baseline_ratings = self.baseline_data["rating"].values
        current_ratings = current_data["rating"].values

        ks_statistic, p_value = stats.ks_2samp(baseline_ratings, current_ratings)

        drift_detected = p_value < threshold

        result = {
            "drift_detected": drift_detected,
            "ks_statistic": float(ks_statistic),
            "p_value": float(p_value),
            "threshold": threshold,
            "baseline_mean": float(self.baseline_stats["rating_mean"]),
            "current_mean": float(current_data["rating"].mean()),
            "mean_difference": float(current_data["rating"].mean() - self.baseline_stats["rating_mean"]),
        }

        if drift_detected:
            logger.warning("Rating drift detected", result=result)
        else:
            logger.info("No significant rating drift detected", p_value=p_value)

        return drift_detected, result

    def detect_popularity_drift(
        self, current_data: pd.DataFrame, top_n: int = 20, threshold: float = 0.3
    ) -> Tuple[bool, Dict[str, Any]]:
        logger.info("Detecting popularity drift", top_n=top_n)

        baseline_top = set(self.baseline_stats["top_products"].keys())
        current_top = set(current_data["product_id"].value_counts().head(top_n).index)

        overlap = len(baseline_top & current_top)
        jaccard_similarity = overlap / len(baseline_top | current_top) if len(baseline_top | current_top) > 0 else 0.0

        drift_detected = jaccard_similarity < (1 - threshold)

        result = {
            "drift_detected": drift_detected,
            "jaccard_similarity": float(jaccard_similarity),
            "overlap": int(overlap),
            "baseline_top_n": list(baseline_top),
            "current_top_n": list(current_top),
            "threshold": threshold,
        }

        if drift_detected:
            logger.warning("Popularity drift detected", result=result)
        else:
            logger.info("No significant popularity drift detected", similarity=jaccard_similarity)

        return drift_detected, result

    def detect_volume_drift(
        self, current_data: pd.DataFrame, threshold: float = 0.2
    ) -> Tuple[bool, Dict[str, Any]]:
        logger.info("Detecting volume drift")

        baseline_volume = self.baseline_stats["total_interactions"]
        current_volume = len(current_data)

        volume_change = abs(current_volume - baseline_volume) / baseline_volume if baseline_volume > 0 else 0.0
        drift_detected = volume_change > threshold

        result = {
            "drift_detected": drift_detected,
            "baseline_volume": int(baseline_volume),
            "current_volume": int(current_volume),
            "volume_change": float(volume_change),
            "threshold": threshold,
        }

        if drift_detected:
            logger.warning("Volume drift detected", result=result)
        else:
            logger.info("No significant volume drift detected", change=volume_change)

        return drift_detected, result

    def detect_all_drift(self, current_data: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Running comprehensive drift detection")

        results = {}

        rating_drift, rating_result = self.detect_rating_drift(current_data)
        results["rating_drift"] = rating_result

        popularity_drift, popularity_result = self.detect_popularity_drift(current_data)
        results["popularity_drift"] = popularity_result

        volume_drift, volume_result = self.detect_volume_drift(current_data)
        results["volume_drift"] = volume_result

        overall_drift = rating_drift or popularity_drift or volume_drift
        results["overall_drift_detected"] = overall_drift

        logger.info("Drift detection complete", overall_drift=overall_drift, results=results)

        return results

