# Monitoring Strategy

## Overview

The ShopAI ML Recommender System includes comprehensive monitoring for observability, debugging, and performance optimization.

## Logging

### Structured Logging

**Library:** Structlog
**Format:** JSON (production) or Console (development)

**Log Levels:**
- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

### Log Context

Every log entry includes:
- `timestamp`: ISO 8601 format
- `request_id`: Unique identifier per request
- `user_id`: User identifier (if available)
- `endpoint`: API endpoint path
- `level`: Log level

### Example Log Entry

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "request_id": "abc123",
  "user_id": "U001",
  "endpoint": "/api/v1/recommendations",
  "message": "Recommendations generated",
  "count": 10,
  "inference_time_ms": 180.3
}
```

### Log Destinations

**Development:**
- Console output (colorized)

**Production (when deployed to AWS):**
- CloudWatch Logs (AWS)
- STDOUT (container logs)

**Current (Local):**
- STDOUT (console output)

## Metrics

### Prometheus Metrics

**Endpoint:** `/metrics`

**HTTP Metrics:**
- `http_requests_total`: Total requests by method, endpoint, status
- `http_request_duration_seconds`: Request duration histogram
- `http_errors_total`: Error count by type

**Application Metrics:**
- `model_inference_duration_seconds`: Model inference time
- `openai_api_calls_total`: OpenAI API call count
- `cache_hits_total`: Cache hit count
- `cache_misses_total`: Cache miss count
- `models_loaded`: Number of loaded models

### Key Metrics to Monitor

**Latency:**
- p50, p95, p99 request duration
- Target: p95 < 200ms for recommendations

**Throughput:**
- Requests per second
- Successful vs failed requests

**Errors:**
- Error rate (errors / total requests)
- Target: < 1% error rate

**Cache Performance:**
- Cache hit rate
- Target: > 70% hit rate

## Health Checks

### Endpoint

`GET /api/v1/health`

### Checks

1. **API Status:** Always healthy if endpoint responds
2. **Models:** Verify collaborative model is loaded
3. **Vector Store:** Verify FAISS index is loaded

### Response States

- `healthy`: All checks pass
- `degraded`: Some checks fail (models not loaded)

### Integration

- ECS: Health check for task definition
- Kubernetes: Liveness and readiness probes
- Load Balancer: Health check endpoint

## Alerting

### Recommended Alerts

**Critical:**
- API down (health check fails)
- Error rate > 5%
- Latency p95 > 1s

**Warning:**
- Error rate > 1%
- Latency p95 > 500ms
- Cache hit rate < 50%
- OpenAI API errors

### Alert Channels

- Email
- Slack
- PagerDuty (for critical alerts)

## Dashboards

### Recommended Dashboards

**1. API Performance**
- Request rate
- Latency (p50, p95, p99)
- Error rate
- Response codes distribution

**2. Model Performance**
- Inference time
- Cache hit rate
- Model load status

**3. Business Metrics**
- Recommendations per user
- Search queries per day
- Popular products

**4. Cost Monitoring**
- OpenAI API calls
- Estimated costs
- Cache efficiency

### Tools

- Grafana (for Prometheus metrics)
- CloudWatch Dashboards (AWS)
- Datadog (alternative)

## Tracing

### Request Tracing

Every request gets a unique `request_id` that:
- Appears in all logs
- Included in response headers (`X-Request-ID`)
- Used for correlation across services

### Distributed Tracing (Future)

Consider implementing:
- OpenTelemetry
- AWS X-Ray
- Jaeger

## Performance Monitoring

### Key Performance Indicators (KPIs)

1. **Response Time:**
   - Recommendations: < 200ms (p95)
   - Search: < 500ms (p95)

2. **Throughput:**
   - Requests per second
   - Concurrent users

3. **Reliability:**
   - Uptime: > 99.9%
   - Error rate: < 1%

4. **Efficiency:**
   - Cache hit rate: > 70%
   - OpenAI API calls: Minimize unnecessary calls

## Monitoring Tools Setup

### Prometheus

```yaml
scrape_configs:
  - job_name: 'shopai-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['shopai-api:8000']
```

### Grafana

Import dashboard with:
- Request rate
- Latency percentiles
- Error rates
- Cache metrics

### CloudWatch

- Log groups: `/aws/ecs/shopai-api`
- Metrics: Custom metrics from Prometheus
- Alarms: Based on thresholds

## Best Practices

1. **Log Aggregation:** Centralize logs for easy searching
2. **Metric Retention:** Keep metrics for at least 30 days
3. **Alert Fatigue:** Set meaningful thresholds
4. **Documentation:** Document all metrics and their meanings
5. **Regular Reviews:** Review metrics weekly for trends

## Troubleshooting

### High Latency
1. Check cache hit rate
2. Monitor OpenAI API latency
3. Review model inference times
4. Check system resources (CPU, memory)

### High Error Rate
1. Check logs for error patterns
2. Verify model files are present
3. Check OpenAI API status
4. Review recent deployments

### Cache Issues
1. Monitor cache hit/miss rates
2. Check Redis connectivity (if used)
3. Review cache TTL settings
4. Verify cache key patterns

