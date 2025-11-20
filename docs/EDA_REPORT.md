# EDA Report - How It Works

## Best Practice: Static Generation (Recommended)

### How It Currently Works

The EDA report is generated **once** as part of the ML pipeline and served statically from the API.

```
ML Pipeline:
  ingest → eda → generate-embeddings → train → evaluate
            ↓
      Generates HTML/JSON report
            ↓
      Saves to data/reports/
            ↓
      API serves static report
```

### Advantages of Static Generation:

1. **Fast**: API only serves an HTML file (milliseconds)
2. **Efficient**: Doesn't consume CPU/memory on each request
3. **Consistent**: Everyone sees the same report
4. **Secure**: Doesn't require access to processed data in the API
5. **Scalable**: Can serve thousands of requests without issues

### When It's Generated:

- **Manually**: `make eda` or `poetry run python scripts/eda.py`
- **In pipeline**: `make pipeline` (includes `make eda`)
- **After ingest**: When there's new data

### Complete Flow:

```bash
# 1. Process data
make ingest

# 2. Generate EDA report (once)
make eda
# Generates:
# - data/reports/eda_report.html
# - data/reports/eda_report.json
# - data/reports/figures/*.png

# 3. Upload to S3 or include in Docker
aws s3 sync data/reports/ s3://shopai-data/ml-recommender/reports/

# 4. API serves static report
# GET /api/v1/reports/eda → HTML
# GET /api/v1/reports/eda/json → JSON
```

---

## Why NOT Generate On-Demand

### Problems with On-Demand Generation:

1. **Slow**: 
   - Load processed data: ~1-2 seconds
   - Process statistics: ~0.5-1 second
   - Generate charts: ~2-3 seconds
   - **Total: 3-6 seconds per request**

2. **Expensive**:
   - Consumes CPU/memory on each request
   - Requires access to processed data
   - Can saturate the server with multiple requests

3. **Inconsistent**:
   - Each request could show slightly different data
   - If data changes during the request, the report would be inconsistent

4. **Security**:
   - Requires access to processed data in the container
   - Larger attack surface

---

## When to Regenerate the Report

### Options:

1. **Manual** (Current):
   ```bash
   make eda  # When you want to update
   ```

2. **Automatic after ingest**:
   ```bash
   make ingest eda  # Regenerates after new data
   ```

3. **In CI/CD Pipeline**:
   ```yaml
   - name: Generate EDA Report
     run: make eda
   - name: Upload to S3
     run: aws s3 sync data/reports/ s3://...
   ```

4. **Cron Job** (if data updates frequently):
   ```bash
   # Run daily
   0 2 * * * cd /path/to/project && make ingest eda
   ```

---

## Current Implementation

### API Endpoints:

```python
# GET /api/v1/reports/eda
# → Serves static HTML
# → If it doesn't exist, tries to download from S3
# → If it doesn't exist in S3, returns 404

# GET /api/v1/reports/eda/json
# → Serves static JSON
# → Same behavior as HTML

# GET /api/v1/reports/eda/figures/{filename}
# → Serves static images (PNG)
```

### Endpoint Code:

```python
@router.get("/eda", response_class=HTMLResponse)
async def get_eda_report():
    report_path = Path("data/reports/eda_report.html")
    
    if not report_path.exists():
        # Try to download from S3
        try:
            download_report_from_s3("eda_report.html")
        except:
            return 404
    
    # Serve static file
    return HTMLResponse(content=html_content)
```

---

## Final Recommendation

### Use Static Generation:

1. **Generate report as part of ML pipeline**
2. **Upload to S3** or **include in Docker image**
3. **API serves static report** (fast and efficient)
4. **Regenerate only when there's new data**

### Recommended Flow:

```bash
# Development/Testing
make ingest eda  # Generate report locally
open data/reports/eda_report.html  # View locally

# Production
make ingest eda  # Generate report
aws s3 sync data/reports/ s3://shopai-data/ml-recommender/reports/  # Upload to S3
# API automatically downloads from S3 if it doesn't exist locally
```

### Advantages:

- Fast (< 100ms to serve HTML)
- Efficient (doesn't consume resources on each request)
- Scalable (can serve thousands of requests)
- Consistent (everyone sees the same report)
- Secure (doesn't require data access at runtime)

---

## Comparison

| Aspect | Static Generation | On-Demand Generation |
|--------|-------------------|---------------------|
| **Speed** | < 100ms | 3-6 seconds |
| **CPU Cost** | Minimal | High |
| **Scalability** | Excellent | Limited |
| **Consistency** | Always same | May vary |
| **Security** | No data required | Requires data |
| **Complexity** | Simple | Complex |

**Conclusion: Static Generation is the best option for production**
