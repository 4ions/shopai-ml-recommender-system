.PHONY: setup install clean test lint format serve docker-build docker-run ingest train evaluate generate-embeddings

setup:
	poetry install

install:
	poetry install --no-dev

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf dist build .coverage htmlcov

test:
	poetry run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	poetry run ruff check src tests
	poetry run mypy src

format:
	poetry run black src tests
	poetry run ruff check --fix src tests

ingest:
	poetry run python scripts/ingest.py --source s3

ingest-local:
	poetry run python scripts/ingest.py --source local

eda:
	poetry run python scripts/eda.py

train:
	poetry run python scripts/train.py

evaluate:
	poetry run python scripts/evaluate.py

generate-embeddings:
	poetry run python scripts/generate_embeddings.py

pipeline: ingest eda generate-embeddings train evaluate
	@echo "Full pipeline completed"

retrain:
	poetry run python scripts/retrain_model.py

refresh-embeddings:
	poetry run python scripts/refresh_embeddings.py

evaluate-production:
	poetry run python scripts/evaluate_production.py

upload-s3:
	poetry run python scripts/upload_to_s3.py --all

download-s3:
	poetry run python scripts/download_from_s3.py --all

regenerate-index:
	poetry run python scripts/regenerate_faiss_index.py

cost-analysis:
	poetry run python scripts/generate_cost_analysis.py

serve:
	poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -f docker/Dockerfile -t shopai-api:latest .

docker-run:
	docker-compose -f docker/docker-compose.yml up --build

