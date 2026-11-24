"""FastAPI приложение."""

from __future__ import annotations

from fastapi import FastAPI

from case_workspace.api.routes import (
    auth,
    cases,
    deadlines,
    identifiers,
    notifications,
)
from case_workspace.api.ws import router as ws_router


def create_app() -> FastAPI:
    app = FastAPI(title="Case Workspace API", version="0.1.0")

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(cases.router, prefix="/api/v1")
    app.include_router(identifiers.router, prefix="/api/v1")
    app.include_router(deadlines.router, prefix="/api/v1")
    app.include_router(notifications.router, prefix="/api/v1")
    app.include_router(ws_router)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    return app


app = create_app()
