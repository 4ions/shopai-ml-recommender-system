# OpenAI Integration Documentation

## Overview

This document describes how the ShopAI system integrates with OpenAI's API for generating embeddings and semantic search capabilities.

## Architecture

### Embedding Generation

**Model Used:** `text-embedding-3-large`
**Dimension:** 1536 (configurable via `OPENAI_EMBEDDING_DIMENSION`)

**Flow:**
1. Product text preparation (name + description + category)
2. Batch processing (100 products per batch)
3. API calls with retry logic
4. Embedding storage and indexing

## Implementation Details

### API Client Setup

```python
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
```

### Key Management

**Local Development:**
- Stored in `.env` file: `OPENAI_API_KEY=your_key_here`
- Never committed to git (`.env` in `.gitignore`)

**Production (AWS):**
- AWS Secrets Manager: `shopai/openai-api-key`
- Accessed via IAM role (no hardcoded keys)

### Batch Processing

**Strategy:**
- Batch size: 100 products (API limit)
- Sequential batches with progress tracking
- Error handling per batch (continues on failure)

**Code:**
```python
for i in range(0, len(product_texts), batch_size):
    batch_texts = product_texts[i : i + batch_size]
    batch_embeddings = []
    for text in batch_texts:
        embedding = get_embedding(client, text)
        batch_embeddings.append(embedding)
    embeddings.extend(batch_embeddings)
```

### Error Handling

**Retry Strategy:**
- Library: `tenacity`
- Max attempts: 3
- Backoff: Exponential (4s, 8s, 16s)

**Implementation:**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_embedding(client: OpenAI, text: str) -> List[float]:
    response = client.embeddings.create(
        model=settings.openai_model_id,
        input=text,
        dimensions=settings.openai_embedding_dimension,
    )
    return response.data[0].embedding
```

### Rate Limiting

**Current Implementation:**
- Sequential processing (respects API rate limits)
- No explicit rate limiting (relies on retry backoff)

**Future Enhancement:**
- Token bucket algorithm
- Request queuing
- Distributed rate limiting for multiple instances

### Latency Management

**Optimizations:**
1. **Caching:** Query embeddings cached (1 hour TTL)
2. **Batch Processing:** Reduces API overhead
3. **Async Processing:** Could be implemented for parallel batches

**Current Performance:**
- Embedding generation: ~40-50ms per product (batch)
- Query embedding: ~150-200ms (first call), <5ms (cached)

### Cost Control

**Strategies:**
1. **Caching:** Avoids redundant API calls
2. **Batch Processing:** Efficient token usage
3. **Dimension Selection:** 1536 vs 3072 (50% cost reduction)

**Monitoring:**
- Prometheus metric: `openai_api_calls_total`
- Tracks: operation type, status (success/error)

**Cost Estimation:**
- 200 products: ~10,000 tokens = $0.0013
- Per search query: ~10 tokens = $0.0000013

### Dimension Configuration

**Current:** 1536 dimensions
**Alternative:** 3072 (default for text-embedding-3-large)

**Trade-offs:**
- 1536: Lower cost, sufficient quality
- 3072: Higher cost, potentially better quality

**Configuration:**
```python
# In settings.py
openai_embedding_dimension: int = 1536
```

## Usage Examples

### Generating Product Embeddings

```python
from src.models.embeddings import generate_embeddings

products = [
    {"product_id": "P001", "name": "Product", "description": "Description", "category": "electronics"}
]
embeddings = generate_embeddings(products, batch_size=100)
```

### Query Embedding

```python
from src.models.embeddings import get_embedding
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
query_embedding = get_embedding(client, "wireless headphones")
```

## Monitoring

### Metrics

- `openai_api_calls_total`: Total API calls
  - Labels: `operation` (embedding), `status` (success/error)

### Logging

All OpenAI API calls are logged with:
- Operation type
- Success/failure status
- Latency
- Error messages (if any)

## Best Practices

1. **Always use retries:** Network issues are common
2. **Batch when possible:** More efficient than individual calls
3. **Cache aggressively:** Query embeddings rarely change
4. **Monitor costs:** Track API usage regularly
5. **Handle errors gracefully:** Continue processing on individual failures

## Troubleshooting

### Common Issues

**Rate Limit Errors:**
- Solution: Reduce batch size or add delays
- Check: Current rate limits in OpenAI dashboard

**Timeout Errors:**
- Solution: Increase timeout or retry
- Check: Network connectivity

**Invalid API Key:**
- Solution: Verify key in `.env` file
- Check: Key has proper permissions

**High Latency:**
- Solution: Enable caching, use async processing
- Check: Network conditions, API status

## Future Enhancements

1. **Async Processing:** Parallel batch requests
2. **Streaming:** For large datasets
3. **Alternative Models:** Support for other embedding models
4. **Fine-tuning:** If applicable for domain-specific use cases

