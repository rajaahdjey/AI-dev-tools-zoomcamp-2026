.PHONY: help install run test
.DEFAULT_GOAL := help

PORT ?= 8000

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## Sync dependencies with uv (Python 3.13)
	uv sync

run: ## Run the API with auto-reload on :$(PORT) (frees the port first)
	@command -v lsof >/dev/null && lsof -ti:$(PORT) | xargs kill -9 2>/dev/null; true
	uv run uvicorn app.main:app --reload --port $(PORT)
test: ## Run the pytest suite
	uv run pytest -q
