# ShopAI ML Recommender System

Hybrid recommendation and semantic search system that combines collaborative filtering and OpenAI embeddings to provide personalized product recommendations and semantic search capabilities.

## Features

- **Collaborative Filtering**: ALS (Alternating Least Squares) model for recommendations based on user-item interactions
- **Semantic Search**: OpenAI embeddings for similarity-based semantic search
- **Hybrid Fusion**: Intelligent combination of both approaches with weight calibration
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Monitoring**: Structured logging, Prometheus metrics, health checks
- **Docker**: Production-ready container with multi-stage build

## Architecture

The system consists of:

- **Data Pipeline**: Ingestion, validation, transformation, and temporal splitting
- **ML Models**: Baseline, collaborative, embeddings, hybrid
- **Services**: Vector store (FAISS), recommendation, search
- **API**: RESTful endpoints with Pydantic validation
- **Infrastructure**: Logging, metrics, caching

## Requirements

- Python 3.11+
- Poetry (for dependency management)
- OpenAI API Key
- (Optional) AWS credentials for S3 (not required for local use)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd shopai-ml-recommender-system
```

2. Install dependencies:
```bash
make setup
# or
poetry install
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## Usage

### Complete Pipeline

1. **Data Ingestion**:
```bash
make ingest
# or
poetry run python scripts/ingest.py
```

2. **Generate Embeddings**:
```bash
make generate-embeddings
# or
poetry run python scripts/generate_embeddings.py
```

3. **Train Models**:
```bash
make train
# or
poetry run python scripts/train.py
```

4. **Evaluate**:
```bash
make evaluate
# or
poetry run python scripts/evaluate.py
```

5. **Start API**:
```bash
make serve
# or
poetry run uvicorn src.api.main:app --reload
```

### Docker

```bash
make docker-build
make docker-run
# or
docker-compose -f docker/docker-compose.yml up --build
```

## API Endpoints

### Semantic Search

```bash
POST /api/v1/search
{
  "query": "wireless headphones with noise cancellation",
  "top_k": 10,
  "filters": {
    "category": "electronics",
    "min_rating": 4.0
  }
}
```

### Recommendations

```bash
POST /api/v1/recommendations
{
  "user_id": "U001",
  "top_k": 10,
  "exclude_seen": true,
  "diversify": false
}
```

### Health Check

```bash
GET /api/v1/health
```

### Metrics

```bash
GET /metrics
```

### Documentation

```bash
GET /docs  # Swagger UI
GET /redoc  # ReDoc
```

## Project Structure

```
shopai-ml-recommender-system/
├── src/
│   ├── config/          # Configuration and settings
│   ├── data/            # Ingestion, validation, transformation
│   ├── models/          # ML models (baseline, collaborative, hybrid)
│   ├── services/        # Business services
│   ├── api/             # FastAPI API
│   └── infrastructure/  # Logging, metrics, cache
├── scripts/             # Automation scripts
├── tests/               # Unit and integration tests
├── data/                # Processed data and artifacts
├── docker/              # Dockerfile and docker-compose
└── docs/                # Additional documentation
```

## Development

### Tests

```bash
make test
# or
poetry run pytest tests/ -v
```

### Linting

```bash
make lint
# or
poetry run ruff check src tests
poetry run mypy src
```

### Formatting

```bash
make format
# or
poetry run black src tests
poetry run ruff check --fix src tests
```

## Evaluation Metrics

The system evaluates models using:

- **Precision@K**: Precision in top K results
- **Recall@K**: Recall in top K results
- **NDCG@K**: Normalized Discounted Cumulative Gain
- **MAP@K**: Mean Average Precision
- **Coverage**: Percentage of recommended items
- **Diversity**: Recommendation diversity

## Costs

The system uses OpenAI for embeddings. Estimated costs:

- Embeddings: ~$0.13 per 1M tokens (text-embedding-3-large)
- For 200 products: ~$0.01-0.02

## Monitoring

- **Logs**: Structured in JSON (production) or readable format (development)
- **Metrics**: Prometheus at `/metrics`
- **Health checks**: Endpoint `/api/v1/health` with model status

## Deployment

### Local

```bash
make serve
```

### Docker

```bash
docker build -f docker/Dockerfile -t shopai-api:latest .
docker run -p 8000:8000 --env-file .env shopai-api:latest
```

### AWS (ECS/EKS) - Optional

The system currently works completely locally. For AWS deployment, see `docs/DEPLOYMENT.md` for detailed instructions.

**Note:** AWS integration (S3, Secrets Manager) is implemented but not used in the current local mode.

## License

MIT

## Author

Leonardo Valencia
