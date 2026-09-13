"""FastAPI app factory. Every error renders as {"error": message}."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .models import ApiError
from .routers import auth as auth_router
from .routers import tasks as tasks_router
from .routers import users as users_router
from .routers import admin as admin_router
from .store import SqlAlchemyStore


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


async def _api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return _error(exc.status, exc.message)


async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else None
    if first is None:
        return _error(422, "Invalid request.")
    loc = ".".join(str(p) for p in first["loc"] if p != "body")
    message = f"{loc}: {first['msg']}" if loc else first["msg"]
    return _error(422, message)


async def _http_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error(exc.status_code, detail)


def create_app(seed: bool = True, database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="Mini Kanban Board API", version="1.0.0")
    app.state.store = SqlAlchemyStore(seed=seed, database_url=database_url)
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.include_router(admin_router.router)
    app.include_router(auth_router.router)
    app.include_router(users_router.router)
    app.include_router(tasks_router.router)
    return app


app = create_app()
