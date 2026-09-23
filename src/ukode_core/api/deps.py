"""Montagem das dependências do Engine a partir da configuração.

Em produção, o registro de conectores e a lista de clientes de LLM vêm de
configuração por tenant (qual CRM, qual ERP, qual WhatsApp). Aqui, para o
esqueleto e a demo, é fixo — ponto claro para expandir."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from ukode_core.approvals.notifiers import ConsoleNotifier, Notifier, WebhookNotifier
from ukode_core.config import settings
from ukode_core.db import SessionLocal
from ukode_core.llm.anthropic_client import AnthropicClient
from ukode_core.llm.base import LLMClient
from ukode_core.llm.fake_client import FakeLLMClient
from ukode_core.mcp_gateway.demo_connector import CRMDemoConnector, WhatsAppDemoConnector
from ukode_core.mcp_gateway.registry import MCPGateway
from ukode_core.orchestrator.agents import load_agents
from ukode_core.orchestrator.engine import Engine
from ukode_core.policy.loader import load_policies


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_llm_clients() -> dict[str, LLMClient]:
    if settings.anthropic_api_key:
        client = AnthropicClient(settings.anthropic_api_key, model=settings.anthropic_model)
        return {"default": client, settings.anthropic_model: client}
    # Sem chave configurada: cai para um cliente roteirizado, para a API
    # continuar de pé em ambiente de demo/lab sem segredo nenhum.
    fake = FakeLLMClient(script=[])
    return {"default": fake, "fake-model": fake}


def build_notifier() -> Notifier:
    if settings.approval_webhook_url:
        return WebhookNotifier(settings.approval_webhook_url)
    return ConsoleNotifier()


def build_mcp_gateway() -> MCPGateway:
    return MCPGateway([WhatsAppDemoConnector(), CRMDemoConnector(contacts={
        "lead@example.com": {"name": "Lead de Exemplo", "phone": "+5511999999999"},
    })])


def build_engine(session: Session) -> Engine:
    agents = load_agents(settings.agents_dir)
    policies = load_policies(settings.policies_dir)
    llm_clients = build_llm_clients()
    mcp_gateway = build_mcp_gateway()
    engine = Engine(session, agents, llm_clients, policies, mcp_gateway)
    return engine.with_approval_notifier(build_notifier())
