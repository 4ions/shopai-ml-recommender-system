# Architecture Documentation

## System Overview

The ShopAI ML Recommender System is a hybrid recommendation and semantic search system that combines collaborative filtering with OpenAI embeddings to provide personalized product recommendations and semantic search capabilities.

## Architecture Components

### 1. Data Layer

**Storage:**
- Raw data: CSV files (transactions, products) - **Currently local only**
- Processed data: Parquet format for efficient columnar storage - **Local filesystem**
- Artifacts: Versioned embeddings, models, and indices - **Stored locally in `data/artifacts/`**
- **Note:** S3 integration is implemented but not currently used. All operations are local.

**Data Flow:**
```
Raw CSV → Validation → Transformation → Parquet → Splitting → Training/Evaluation
```

### 2. Processing Pipeline

**Components:**
- **Ingestion**: Loads data from S3 or local files with streaming support
- **Validation**: Schema validation using Pydantic models
- **Transformation**: Normalization, deduplication, filtering
- **EDA**: Exploratory data analysis with quality reports
- **Splitting**: Temporal split (70/15/15) to prevent data leakage

### 3. ML Models

**Collaborative Filtering:**
- Algorithm: Alternating Least Squares (ALS) via `implicit` library
- Input: User-item interaction matrix (ratings)
- Output: User and item latent factors
- Hyperparameters: factors (50), iterations (15), regularization (0.1)

**Embeddings:**
- Model: OpenAI `text-embedding-3-large`
- Dimension: 1536 (configurable)
- Generation: Batch processing with retry logic
- Storage: FAISS index for efficient similarity search

**Hybrid Fusion:**
- Strategy: Weighted sum or Reciprocal Rank Fusion (RRF)
- Components: Collaborative scores + Semantic similarity scores
- Calibration: Grid search on validation set
- Re-ranking: Diversification using MMR (Maximal Marginal Relevance)

### 4. Vector Store

**Implementation:**
- Library: FAISS (Facebook AI Similarity Search)
- Index Type: InnerProduct (for cosine similarity) or L2 (Euclidean)
- Normalization: L2 normalization for cosine similarity
- Persistence: Pickle serialization with metadata

### 5. API Service

**Framework:** FastAPI
**Endpoints:**
- `POST /api/v1/search`: Semantic search
- `POST /api/v1/recommendations`: Hybrid recommendations
- `GET /api/v1/health`: Health check
- `GET /metrics`: Prometheus metrics
- `POST /api/v1/feedback`: User feedback collection

**Features:**
- Async request handling
- Structured logging with correlation IDs
- Prometheus metrics integration
- Caching (in-memory or Redis)
- Input validation with Pydantic

### 6. Infrastructure

**Logging:**
- Library: Structlog
- Format: JSON (production) or console (development)
- Context: Request IDs, user IDs, timestamps

**Metrics:**
- Library: Prometheus client
- Metrics: Request count, duration, errors, cache hits/misses
- Export: `/metrics` endpoint

**Caching:**
- Strategy: LRU cache with TTL
- Backend: DiskCache (local) or Redis (production)
- Keys: User-based for recommendations, query-based for search

## Design Patterns

### Repository Pattern
Data access is abstracted through repository-like functions in `src/data/ingestion.py`

### Strategy Pattern
Different recommendation strategies (popularity, collaborative, hybrid) are interchangeable

### Factory Pattern
Model creation and loading handled through factory methods

### Dependency Injection
FastAPI's `Depends()` used for service injection

## Data Flow

### Training Pipeline
```
CSV → Ingest → Validate → Transform → Split → Train → Evaluate → Save Artifacts
```

### Inference Pipeline
```
Request → Validate → Load Models → Generate Candidates → Fuse → Re-rank → Return
```

## Scalability Considerations

**Current:**
- Local FAISS index (suitable for < 1M vectors)
- In-memory caching
- Single-instance API

**Future:**
- Distributed FAISS (sharding)
- Redis cluster for caching
- Horizontal scaling with load balancer
- PGVector/OpenSearch for production vector store

## Security

- Environment variables for sensitive data
- AWS Secrets Manager integration (production)
- IAM roles for S3 access
- Input validation and sanitization
- Rate limiting

## Performance

**Target Latencies:**
- Recommendations: < 200ms (p95)
- Search: < 500ms (p95)
- Health check: < 10ms

**Optimizations:**
- Caching of frequent queries
- Batch embedding generation
- FAISS index optimization
- Async request handling

