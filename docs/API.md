# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. For production, implement API keys or OAuth2.

## Endpoints

### 1. Search (Semantic)

Search for products using natural language queries.

**Endpoint:** `POST /api/v1/search`

**Request Body:**
```json
{
  "query": "wireless headphones with noise cancellation",
  "top_k": 10,
  "filters": {
    "category": "electronics",
    "min_rating": 4.0,
    "min_interactions": 10
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "product_id": "P001",
      "score": 0.85,
      "name": "Wireless Headphones",
      "category": "electronics",
      "description": "High quality wireless device...",
      "avg_rating": 4.5,
      "total_interactions": 150
    }
  ],
  "query_embedding_time_ms": 150.5,
  "search_time_ms": 5.2,
  "total_time_ms": 155.7
}
```

**Status Codes:**
- `200`: Success
- `400`: Bad request (invalid input)
- `500`: Internal server error

### 2. Recommendations

Get personalized product recommendations for a user.

**Endpoint:** `POST /api/v1/recommendations`

**Request Body:**
```json
{
  "user_id": "U001",
  "top_k": 10,
  "exclude_seen": true,
  "include_metadata": true,
  "diversify": false
}
```

**Response:**
```json
{
  "user_id": "U001",
  "recommendations": [
    {
      "product_id": "P119",
      "score": 0.75,
      "name": "Product Name",
      "category": "electronics",
      "description": "Product description",
      "avg_rating": 4.2,
      "total_interactions": 47
    }
  ],
  "model_version": "v1.0",
  "inference_time_ms": 180.3
}
```

**Status Codes:**
- `200`: Success
- `404`: User not found
- `400`: Bad request
- `500`: Internal server error

### 3. Health Check

Check the health status of the API and loaded models.

**Endpoint:** `GET /api/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "api": "healthy",
    "models": "loaded",
    "vector_store": "loaded"
  }
}
```

**Status Codes:**
- `200`: Healthy
- `503`: Degraded (models not loaded)

### 4. Metrics

Expose Prometheus metrics for monitoring.

**Endpoint:** `GET /metrics`

**Response:** Prometheus format text

**Metrics:**
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration histogram
- `http_errors_total`: Total HTTP errors
- `model_inference_duration_seconds`: Model inference time
- `openai_api_calls_total`: OpenAI API calls
- `cache_hits_total`: Cache hits
- `cache_misses_total`: Cache misses

### 5. Feedback

Submit user feedback on recommendations.

**Endpoint:** `POST /api/v1/feedback`

**Request Body:**
```json
{
  "user_id": "U001",
  "product_id": "P119",
  "relevant": true,
  "recommendation_id": "rec_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Feedback recorded successfully"
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

## Rate Limiting

- Per IP: 100 requests/minute
- Global: 1000 requests/minute

## Examples

### Python

```python
import requests

# Search
response = requests.post(
    "http://localhost:8000/api/v1/search",
    json={"query": "electronics", "top_k": 5}
)
print(response.json())

# Recommendations
response = requests.post(
    "http://localhost:8000/api/v1/recommendations",
    json={"user_id": "U001", "top_k": 10}
)
print(response.json())
```

### cURL

```bash
# Search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "electronics", "top_k": 5}'

# Recommendations
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id": "U001", "top_k": 10}'
```

## Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

