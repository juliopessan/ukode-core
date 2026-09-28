"""Registro de agentes: responde 'que agentes existem, quem é dono de cada
um, e onde estão rodando de verdade' — a pergunta que resolve o problema do
agente fantasma."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ukode_core.api.deps import get_db
from ukode_core.api.schemas import AgentOut, CreateFindingRequest, FindingOut
from ukode_core.config import settings
from ukode_core.orchestrator.agents import load_agents
from ukode_core.orchestrator.registry import build_registry, registry_entry
from ukode_core.telemetry.findings import FindingService

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
        evaluators=d.evaluators,
        total_runs=entry.total_runs,
        last_run_at=entry.last_run_at,
        total_cost_usd=entry.total_cost_usd,
        tenants=entry.tenants,
    )


def _finding_out(f) -> FindingOut:
    return FindingOut(
        id=f.id,
        agent_id=f.agent_id,
        run_id=f.run_id,
        severity=f.severity,
        finding=f.finding,
        reported_by=f.reported_by,
        created_at=f.created_at.isoformat(),
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


@router.post("/{agent_id}/findings", response_model=FindingOut)
def report_finding(
    agent_id: str, body: CreateFindingRequest, db: Session = Depends(get_db)
) -> FindingOut:
    agents = load_agents(settings.agents_dir)
    agent = agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    # Papel restrito: só quem está declarado como avaliador (ou o dono) pode
    # registrar um achado. Sem evaluators configurados, o agente ainda não
    # tem observador independente — só o dono pode reportar.
    allowed = set(agent.evaluators) | {agent.owner}
    if body.reported_by not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"'{body.reported_by}' não está na lista de avaliadores de '{agent_id}'",
        )
    findings = FindingService(db)
    record = findings.report(
        agent_id=agent_id,
        finding=body.finding,
        reported_by=body.reported_by,
        severity=body.severity,
        run_id=body.run_id,
    )
    db.commit()
    return _finding_out(record)


@router.get("/{agent_id}/findings", response_model=list[FindingOut])
def list_findings(agent_id: str, db: Session = Depends(get_db)) -> list[FindingOut]:
    findings = FindingService(db)
    return [_finding_out(f) for f in findings.for_agent(agent_id)]
