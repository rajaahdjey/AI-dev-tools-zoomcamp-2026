# Full-stack image: Node builds the frontend, then a slim Python image
# serves the API plus the built static files from the backend.
# Build from the homework root:  docker build -t kanban .
# Run (persist the DB outside the container):
#   docker run -p 8000:8000 -v kanban-data:/data kanban

# ---- frontend build ----
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- backend + statics ----
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 \
    PORT=8000 \
    DATABASE_URL=sqlite:////data/kanban.db \
    FRONTEND_DIR=/app/static
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY --from=frontend /build/dist ./static
EXPOSE 8000
# NOTE: single worker — sessions live in process memory and SQLite
# dislikes concurrent writers. Do not --workers > 1 without moving
# sessions out of process and switching DATABASE_URL to Postgres.
CMD .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
