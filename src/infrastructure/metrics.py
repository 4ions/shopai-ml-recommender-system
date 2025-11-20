from typing import Optional
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)

http_errors_total = Counter(
    "http_errors_total",
    "Total number of HTTP errors",
    ["method", "endpoint", "error_type"],
)

model_inference_duration_seconds = Histogram(
    "model_inference_duration_seconds",
    "Model inference duration in seconds",
    ["model_type", "operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5),
)

openai_api_calls_total = Counter(
    "openai_api_calls_total",
    "Total number of OpenAI API calls",
    ["operation", "status"],
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache_type", "operation"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache_type", "operation"],
)

models_loaded = Gauge(
    "models_loaded",
    "Number of models currently loaded",
    ["model_type"],
)


def get_metrics() -> bytes:
    return generate_latest()


def get_metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST

