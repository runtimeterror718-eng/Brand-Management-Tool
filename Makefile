.PHONY: install setup-models worker beat frontend test lint clean setup

# Full setup for fresh clone
setup: install setup-models
	@echo ""
	@echo "Setup complete. Next steps:"
	@echo "  1. cp .env.example .env"
	@echo "  2. cp secrets/.env.keys.example secrets/.env.keys"
	@echo "  3. cp oval/.env.local.example oval/.env.local"
	@echo "  4. Fill in your API keys in secrets/.env.keys and oval/.env.local"
	@echo "  5. Start Redis: redis-server"
	@echo "  6. make worker  (in one terminal)"
	@echo "  7. make beat    (in another terminal)"
	@echo "  8. make frontend (in another terminal)"
	@echo ""

# Install Python dependencies
install:
	pip install -r requirements.txt
	playwright install chromium

# Download NLP models (fastText + HuggingFace)
setup-models:
	bash scripts/setup_models.sh

# Run Celery worker
worker:
	celery -A workers.celery_app worker --loglevel=info

# Run Celery beat scheduler
beat:
	celery -A workers.celery_app beat --loglevel=info

# Run Next.js frontend (OVAL dashboard on localhost:3000)
frontend:
	cd oval && npm install && npm run dev

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
