"""Serviço de custo: registra cada chamada de modelo e barra a próxima chamada
antes de estourar o orçamento — item 06 da camada UKode."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from ukode_core.ledger.pricing import cost_usd
from ukode_core.llm.base import LLMUsage
from ukode_core.models import BudgetLimit, LedgerEntry


class BudgetExceeded(Exception):
    def __init__(self, tenant_id: str, spent: float, limit: float):
        self.tenant_id = tenant_id
        self.spent = spent
        self.limit = limit
        super().__init__(
            f"orçamento excedido para tenant '{tenant_id}': ${spent:.2f} de ${limit:.2f}"
        )


class LedgerService:
    def __init__(self, session: Session):
        self._session = session

    def _period_start(self, period: str) -> datetime:
        now = datetime.now(UTC).replace(tzinfo=None)
        if period == "daily":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def spent_since(self, tenant_id: str, since: datetime, agent_id: str | None = None) -> float:
        query = self._session.query(func.coalesce(func.sum(LedgerEntry.cost_usd), 0)).filter(
            LedgerEntry.tenant_id == tenant_id, LedgerEntry.created_at >= since
        )
        if agent_id:
            query = query.filter(LedgerEntry.agent_id == agent_id)
        return float(query.scalar() or 0)

    def check_budget(self, tenant_id: str, agent_id: str) -> None:
        limits = (
            self._session.query(BudgetLimit)
            .filter(
                BudgetLimit.tenant_id == tenant_id,
                (BudgetLimit.agent_id == agent_id) | (BudgetLimit.agent_id.is_(None)),
            )
            .all()
        )
        for limit in limits:
            since = self._period_start(limit.period)
            spent = self.spent_since(tenant_id, since, agent_id if limit.agent_id else None)
            if spent >= float(limit.limit_usd):
                raise BudgetExceeded(tenant_id, spent, float(limit.limit_usd))

    def record(
        self, run_id: str, tenant_id: str, agent_id: str, model: str, usage: LLMUsage
    ) -> LedgerEntry:
        entry = LedgerEntry(
            run_id=run_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=cost_usd(model, usage.input_tokens, usage.output_tokens),
        )
        self._session.add(entry)
        self._session.flush()
        return entry
