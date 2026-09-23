from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from ukode_core.db import Base, make_engine
from ukode_core.mcp_gateway.demo_connector import CRMDemoConnector, WhatsAppDemoConnector
from ukode_core.mcp_gateway.registry import MCPGateway
from ukode_core.orchestrator.agents import load_agents
from ukode_core.policy.loader import load_policies

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "src" / "ukode_core" / "orchestrator" / "agents"
POLICIES_DIR = REPO_ROOT / "src" / "ukode_core" / "policy" / "policies"


@pytest.fixture()
def db_session():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def agents():
    return load_agents(AGENTS_DIR)


@pytest.fixture()
def policy_engine():
    return load_policies(POLICIES_DIR)


@pytest.fixture()
def whatsapp_connector():
    return WhatsAppDemoConnector()


@pytest.fixture()
def crm_connector():
    return CRMDemoConnector(contacts={"lead@example.com": {"name": "Lead", "phone": "+5511999999999"}})


@pytest.fixture()
def mcp_gateway(whatsapp_connector, crm_connector):
    return MCPGateway([whatsapp_connector, crm_connector])
