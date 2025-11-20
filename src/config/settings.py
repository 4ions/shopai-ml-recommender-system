from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket: str = "shopai-data"
    s3_prefix: str = "ml-recommender"

    # OpenAI Configuration
    openai_api_key: str
    openai_model_id: str = "text-embedding-3-large"
    openai_embedding_dimension: int = 1536

    # FAISS Configuration
    faiss_index_type: str = "InnerProduct"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # Cache Configuration
    cache_type: str = "memory"
    redis_url: Optional[str] = None
    cache_ttl_recommendations: int = 300
    cache_ttl_search: int = 3600

    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_global_per_minute: int = 1000

    def get_s3_path(self, artifact_type: str, version: str, filename: str) -> str:
        return f"{self.s3_prefix}/{artifact_type}/{version}/{filename}"

    def get_local_data_path(self, subpath: str) -> str:
        return f"data/{subpath}"


settings = Settings()

