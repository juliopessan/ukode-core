"""Registro de execução: responde, para qualquer run, as oito perguntas que
uma auditoria de agente precisa conseguir responder sem vasculhar JSON solto:

  qual agente executou / quem é o dono / qual versão estava ativa /
  qual modelo participou / qual prompt foi usado / quais políticas foram
  aplicadas / quais recursos foram acessados / quanto a execução consumiu

mais o que de fato aconteceu, e se a trilha de auditoria está íntegra. Isso
é o que torna uma execução investigável — e reexecutável — depois do fato,
não só logada."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ukode_core.models import LedgerEntry, PolicyDecision, Run
from ukode_core.orchestrator.agents import AgentDefinition
from ukode_core.telemetry.audit import AuditLog


def _first_user_prompt(run: Run) -> str | None:
    for message in run.messages:
        if message.get("role") == "user":
            for block in message.get("content", []):
                if block.get("type") == "text":
                    return block["text"]
    return None


def build_execution_record(
    session: Session, run: Run, agents: dict[str, AgentDefinition]
) -> dict:
    agent = agents.get(run.agent_id)

    total_cost = session.execute(
        select(LedgerEntry).where(LedgerEntry.run_id == run.id)
    ).scalars().all()
    cost_usd = sum(float(e.cost_usd) for e in total_cost)
    models_used = sorted({e.model for e in total_cost})

    decisions = session.execute(
        select(PolicyDecision)
        .where(PolicyDecision.run_id == run.id)
        .order_by(PolicyDecision.created_at)
    ).scalars().all()

    resources_accessed = sorted(
        {d.tool_name for d in decisions if d.outcome == "allow"}
    )

    return {
        "run_id": run.id,
        "agent_id": run.agent_id,
        "agent_owner": agent.owner if agent else "",
        "agent_version": agent.version if agent else "",
        "model": ", ".join(models_used) if models_used else (agent.model if agent else ""),
        "prompt": _first_user_prompt(run),
        "policies_applied": [
            {
                "tool_name": d.tool_name,
                "tool_args": d.tool_args,
                "outcome": d.outcome,
                "reason": d.reason,
                "created_at": d.created_at.isoformat(),
            }
            for d in decisions
        ],
        "resources_accessed": resources_accessed,
        "cost_usd": cost_usd,
        "status": run.status,
        "result_text": run.result_text,
        "cost_anomaly": run.cost_anomaly,
        "cost_anomaly_reason": run.cost_anomaly_reason,
        "audit_chain_valid": AuditLog(session).verify_chain(run.id),
    }
