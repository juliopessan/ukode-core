"""Registro de agentes: responde 'que agentes existem, quem é dono de cada
um, e onde estão rodando de verdade' — a pergunta que resolve o problema do
agente fantasma."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ukode_core.api.deps import get_db
from ukode_core.api.schemas import AgentOut
from ukode_core.config import settings
from ukode_core.orchestrator.agents import load_agents
from ukode_core.orchestrator.registry import build_registry, registry_entry

router = APIRouter(prefix="/agents", tags=["agents"])


def _to_out(entry) -> AgentOut:
    d = entry.definition
    return AgentOut(
        agent_id=d.agent_id,
        owner=d.owner,
        status=d.status,
        version=d.version,
        description=d.description,
        model=d.model,
        tool_names=d.tool_names,
        total_runs=entry.total_runs,
        last_run_at=entry.last_run_at,
        total_cost_usd=entry.total_cost_usd,
        tenants=entry.tenants,
    )


@router.get("", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)) -> list[AgentOut]:
    agents = load_agents(settings.agents_dir)
    return [_to_out(e) for e in build_registry(db, agents)]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> AgentOut:
    agents = load_agents(settings.agents_dir)
    entry = registry_entry(db, agents, agent_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    return _to_out(entry)
