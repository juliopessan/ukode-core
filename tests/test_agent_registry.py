"""O registro de agentes: resolve 'que agentes existem, quem é dono, e onde
estão rodando' — combinando a declaração YAML com fatos ao vivo do Postgres."""

from __future__ import annotations

from ukode_core.models import LedgerEntry, Run, RunStatus
from ukode_core.orchestrator.agents import AgentStatus
from ukode_core.orchestrator.registry import build_registry, registry_entry


def test_agent_definition_carries_ownership_metadata(agents):
    agent = agents["demo_agent"]
    assert agent.owner == "ops@ukodelabs.com"
    assert agent.status == AgentStatus.ACTIVE
    assert agent.version == "1"
    assert agent.description  # não vazio — todo agente precisa de descrição


def test_registry_reports_zero_runs_for_a_never_used_agent(db_session, agents):
    entries = build_registry(db_session, agents)
    entry = next(e for e in entries if e.definition.agent_id == "demo_agent")

    assert entry.total_runs == 0
    assert entry.last_run_at is None
    assert entry.total_cost_usd == 0
    assert entry.tenants == []


def test_registry_reflects_runs_that_actually_happened(db_session, agents):
    run = Run(tenant_id="acme", agent_id="demo_agent", status=RunStatus.DONE, messages=[])
    db_session.add(run)
    db_session.flush()
    db_session.add(
        LedgerEntry(
            run_id=run.id,
            tenant_id="acme",
            agent_id="demo_agent",
            model="claude-sonnet-5",
            input_tokens=1000,
            output_tokens=200,
            cost_usd=0.006,
        )
    )
    db_session.flush()

    entry = registry_entry(db_session, agents, "demo_agent")

    assert entry.total_runs == 1
    assert entry.last_run_at is not None
    assert entry.total_cost_usd == 0.006
    assert entry.tenants == ["acme"]


def test_registry_entry_is_none_for_unknown_agent(db_session, agents):
    assert registry_entry(db_session, agents, "ghost_agent") is None
