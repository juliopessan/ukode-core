from __future__ import annotations

from fastapi import FastAPI

from ukode_core.api.routes import approvals, health, runs
from ukode_core.config import settings
from ukode_core.db import init_db
from ukode_core.telemetry.otel import configure_telemetry


def create_app() -> FastAPI:
    app = FastAPI(
        title="ukode-core",
        description="Camada de orquestração de agentes de IA da UKode Labs.",
        version="0.1.0",
    )

    @app.on_event("startup")
    def _startup() -> None:
        configure_telemetry(otlp_endpoint=settings.otel_exporter_otlp_endpoint)
        init_db()

    app.include_router(health.router)
    app.include_router(runs.router)
    app.include_router(approvals.router)
    return app


app = create_app()
