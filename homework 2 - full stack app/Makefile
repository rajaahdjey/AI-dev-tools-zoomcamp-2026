.PHONY: help install dev backend frontend test build
.DEFAULT_GOAL := help

# Backend serves :8000, matching the /api proxy in frontend/vite.config.js.

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## Install backend + frontend dependencies
	$(MAKE) -C backend install
	npm --prefix frontend ci

dev: ## Run backend + frontend together (Ctrl-C stops both; frees 5173 first)
	@command -v lsof >/dev/null && lsof -ti:5173 | xargs kill -9 2>/dev/null; true
	trap 'kill 0' INT TERM; \
	$(MAKE) -C backend run & \
	npm --prefix frontend run dev & \
	wait
backend: ## Run the backend API only
	$(MAKE) -C backend run

frontend: ## Run the frontend dev server only
	npm --prefix frontend run dev

test: ## Run the backend test suite
	$(MAKE) -C backend test

build: ## Production-build the frontend
	npm --prefix frontend run build
