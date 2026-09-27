"""O registro de agentes: a declaração estática (YAML) somada a fatos ao
vivo tirados do Postgres — quantos runs, quando foi o último, quanto já
custou, em quais tenants está rodando. Isso é o que responde "que agentes
existem e onde estão rodando de verdade", não só "que agentes declaramos"."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ukode_core.models import LedgerEntry, Run
from ukode_core.orchestrator.agents import AgentDefinition


@dataclass
class AgentRegistryEntry:
    definition: AgentDefinition
    total_runs: int
    last_run_at: str | None
    total_cost_usd: float
    tenants: list[str]


def _stats_for_agent(session: Session, agent_id: str) -> dict:
    total_runs = session.execute(
        select(func.count(Run.id)).where(Run.agent_id == agent_id)
    ).scalar_one()
    last_run_at = session.execute(
        select(func.max(Run.created_at)).where(Run.agent_id == agent_id)
    ).scalar_one()
    total_cost = session.execute(
        select(func.coalesce(func.sum(LedgerEntry.cost_usd), 0)).where(
            LedgerEntry.agent_id == agent_id
        )
    ).scalar_one()
    tenants = session.execute(
        select(Run.tenant_id).where(Run.agent_id == agent_id).distinct()
    ).scalars().all()
    return {
        "total_runs": total_runs,
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "total_cost_usd": float(total_cost),
        "tenants": sorted(tenants),
    }


def build_registry(
    session: Session, agents: dict[str, AgentDefinition]
) -> list[AgentRegistryEntry]:
    entries = []
    for agent in agents.values():
        stats = _stats_for_agent(session, agent.agent_id)
        entries.append(
            AgentRegistryEntry(
                definition=agent,
                total_runs=stats["total_runs"],
                last_run_at=stats["last_run_at"],
                total_cost_usd=stats["total_cost_usd"],
                tenants=stats["tenants"],
            )
        )
    return entries


def registry_entry(
    session: Session, agents: dict[str, AgentDefinition], agent_id: str
) -> AgentRegistryEntry | None:
    agent = agents.get(agent_id)
    if agent is None:
        return None
    stats = _stats_for_agent(session, agent_id)
    return AgentRegistryEntry(
        definition=agent,
        total_runs=stats["total_runs"],
        last_run_at=stats["last_run_at"],
        total_cost_usd=stats["total_cost_usd"],
        tenants=stats["tenants"],
    )
