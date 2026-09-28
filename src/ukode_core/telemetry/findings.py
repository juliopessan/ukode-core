"""Serviço de achados de avaliação: o papel de avaliador independente,
separado de quem opera e de quem aprova (approvals/service.py). Um achado
nunca bloqueia nada — só fica registrado e visível. Se o avaliador precisar
impedir uma ação, isso é uma política (policy/), não um achado."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ukode_core.models import EvaluationFinding, FindingSeverity


class FindingService:
    def __init__(self, session: Session):
        self._session = session

    def report(
        self,
        agent_id: str,
        finding: str,
        reported_by: str,
        severity: str = FindingSeverity.INFO,
        run_id: str | None = None,
    ) -> EvaluationFinding:
        record = EvaluationFinding(
            agent_id=agent_id,
            run_id=run_id,
            severity=severity,
            finding=finding,
            reported_by=reported_by,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def for_agent(self, agent_id: str) -> list[EvaluationFinding]:
        return list(
            self._session.execute(
                select(EvaluationFinding)
                .where(EvaluationFinding.agent_id == agent_id)
                .order_by(EvaluationFinding.created_at.desc())
            ).scalars()
        )

    def for_run(self, run_id: str) -> list[EvaluationFinding]:
        return list(
            self._session.execute(
                select(EvaluationFinding)
                .where(EvaluationFinding.run_id == run_id)
                .order_by(EvaluationFinding.created_at.desc())
            ).scalars()
        )
