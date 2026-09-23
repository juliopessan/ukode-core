"""Configuração da aplicação, lida de variáveis de ambiente / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./ukode_core.db"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    oidc_issuer: str = ""
    oidc_audience: str = ""

    approval_webhook_url: str = ""

    otel_exporter_otlp_endpoint: str = ""

    policies_dir: str = "src/ukode_core/policy/policies"
    agents_dir: str = "src/ukode_core/orchestrator/agents"


settings = Settings()
