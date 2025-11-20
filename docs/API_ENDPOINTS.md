# API Endpoints Guide

## Base URL

```
http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com
```

---

## 1. Semantic Search

### Endpoint
```
POST /api/v1/search
```

### Description
Search products using semantic search based on OpenAI embeddings.

### Body (JSON)
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

### Fields
- **query** (required): Search text (1-500 characters)
- **top_k** (optional): Number of results (1-100, default: 10)
- **filters** (optional): Optional filters
  - `category`: Filter by category
  - `min_rating`: Minimum rating
  - `min_interactions`: Minimum interactions

### Example with cURL
```bash
curl -X POST http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wireless headphones",
    "top_k": 5
  }'
```

### Example with Python
```python
import requests

url = "http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/search"
response = requests.post(url, json={
    "query": "wireless headphones",
    "top_k": 5
})
print(response.json())
```

### Response
```json
{
  "results": [
    {
      "product_id": "P001",
      "score": 0.95,
      "name": "Wireless Headphones",
      "category": "electronics",
      "description": "Premium wireless headphones",
      "avg_rating": 4.5,
      "total_interactions": 150
    }
  ],
  "query_embedding_time_ms": 150.5,
  "search_time_ms": 25.3,
  "total_time_ms": 175.8
}
```

---

## 2. Recommendations

### Endpoint
```
POST /api/v1/recommendations
```

### Description
Get personalized recommendations for a user using the hybrid model (collaborative + semantic).

### Body (JSON)
```json
{
  "user_id": "U001",
  "top_k": 10,
  "exclude_seen": true,
  "diversify": false
}
```

### Fields
- **user_id** (required): User ID
- **top_k** (optional): Number of recommendations (1-100, default: 10)
- **exclude_seen** (optional): Exclude already seen products (default: true)
- **diversify** (optional): Apply diversification (default: false)

### Example with cURL
```bash
curl -X POST http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "U001",
    "top_k": 5
  }'
```

### Example with Python
```python
import requests

url = "http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/recommendations"
response = requests.post(url, json={
    "user_id": "U001",
    "top_k": 5,
    "exclude_seen": True
})
print(response.json())
```

### Response
```json
{
  "user_id": "U001",
  "recommendations": [
    {
      "product_id": "P026",
      "score": 0.85,
      "name": "Product Name",
      "category": "electronics",
      "description": "Product description",
      "avg_rating": 4.2,
      "total_interactions": 120
    }
  ],
  "model_version": "v1.0",
  "inference_time_ms": 45.2
}
```

---

## 3. Feedback

### Endpoint
```
POST /api/v1/feedback
```

### Description
Send user feedback about recommendations or products.

### Body (JSON)
```json
{
  "user_id": "U001",
  "product_id": "P001",
  "rating": 5,
  "feedback_type": "explicit"
}
```

### Fields
- **user_id** (required): User ID
- **product_id** (required): Product ID
- **rating** (required): Rating (1-5)
- **feedback_type** (optional): Feedback type ("explicit" or "implicit")

### Example
```bash
curl -X POST http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "U001",
    "product_id": "P001",
    "rating": 5,
    "feedback_type": "explicit"
  }'
```

---

## 4. Health Check

### Endpoint
```
GET /api/v1/health
```

### Description
Check service status and loaded models.

### Example
```bash
curl http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/health
```

### Response
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

---

## 5. EDA Report

### Endpoint
```
GET /api/v1/reports/eda
```

### Description
Get the HTML exploratory data analysis report.

### Example
```bash
curl http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/reports/eda
```

### JSON
```
GET /api/v1/reports/eda/json
```

### Generate Report
```
POST /api/v1/reports/eda/generate
```

---

## Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search` | POST | Semantic search |
| `/api/v1/recommendations` | POST | Personalized recommendations |
| `/api/v1/feedback` | POST | Send feedback |
| `/api/v1/health` | GET | Health check |
| `/api/v1/reports/eda` | GET | EDA HTML report |
| `/api/v1/reports/eda/json` | GET | EDA JSON report |
| `/api/v1/reports/eda/generate` | POST | Generate EDA report |
| `/docs` | GET | Swagger UI documentation |
| `/redoc` | GET | ReDoc documentation |
| `/metrics` | GET | Prometheus metrics |

---

## Complete Examples

### Simple Search
```bash
curl -X POST http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "electronics", "top_k": 5}'
```

### User Recommendations
```bash
curl -X POST http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id": "U001", "top_k": 10}'
```

### Search with Filters
```bash
curl -X POST http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "headphones",
    "top_k": 10,
    "filters": {
      "min_rating": 4.0,
      "category": "electronics"
    }
  }'
```

---

## Interactive Documentation

You can view the complete documentation at:
- **Swagger UI**: `http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/docs`
- **ReDoc**: `http://shopai-api-alb-1869077718.us-east-1.elb.amazonaws.com/redoc`
