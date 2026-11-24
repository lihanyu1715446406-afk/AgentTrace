"""FastAPI 应用入口。

从项目根目录启动：
    uv run python -m uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from .api.routes import (
    diagnose,
    evaluation,
    health,
    ingest,
    knowledge,
    overview,
    projects,
    traces,
)
from .core.config import get_settings
from .core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(ingest.router)
app.include_router(traces.router)
app.include_router(overview.router)
app.include_router(diagnose.router)
app.include_router(knowledge.router)
app.include_router(evaluation.router)
