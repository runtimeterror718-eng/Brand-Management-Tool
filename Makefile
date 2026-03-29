.PHONY: install setup-models dev worker beat frontend test lint clean

# Install Python dependencies
install:
	pip install -r requirements.txt
	playwright install chromium

# Download NLP models
setup-models:
	bash setup_models.sh

# Run the API server (dev)
dev:
	python -m uvicorn api:app --reload --port 8000

# Run Celery worker
worker:
	celery -A workers.celery_app worker --loglevel=info

# Run Celery beat scheduler
beat:
	celery -A workers.celery_app beat --loglevel=info

# Run React frontend
frontend:
	cd frontend && npm install && npm start

# Run tests
test:
	python -m pytest tests/ -v

# Lint
lint:
	ruff check .

# Clean artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .eggs/ *.egg-info/ dist/ build/
