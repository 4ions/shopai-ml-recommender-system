FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry lock --no-update || poetry lock && \
    poetry install --without dev --no-root

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN if [ -d "data/artifacts" ] && [ "$(ls -A data/artifacts 2>/dev/null)" ]; then \
        echo "Artifacts found, copying..."; \
    else \
        echo "No artifacts found locally, will download from S3 at runtime"; \
        mkdir -p data/artifacts; \
    fi && \
    if [ -d "data/reports" ]; then \
        echo "Reports found, copying..."; \
        mkdir -p data/reports/figures; \
    else \
        echo "No reports found, will be generated at runtime if needed"; \
        mkdir -p data/reports/figures; \
    fi

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

