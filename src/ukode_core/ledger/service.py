"""Serviço de custo: registra cada chamada de modelo e barra a próxima chamada
antes de estourar o orçamento — item 06 da camada UKode."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ukode_core.ledger.pricing import cost_usd
from ukode_core.llm.base import LLMUsage
from ukode_core.models import BudgetLimit, LedgerEntry, Run, RunStatus

# Uma execução custando mais que isso em relação à média histórica do mesmo
# agente é sinalizada como anômala — "a execução que pareceu normal e custou
# mais". Não bloqueia nada; só marca o run pra alguém olhar.
ANOMALY_MULTIPLIER = 3.0
# Não julga anomalia sem um histórico mínimo — 3x a média de uma única
# execução anterior não significa nada.
ANOMALY_MIN_SAMPLES = 5


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

    def total_cost_for_run(self, run_id: str) -> float:
        total = self._session.execute(
            select(func.coalesce(func.sum(LedgerEntry.cost_usd), 0)).where(
                LedgerEntry.run_id == run_id
            )
        ).scalar_one()
        return float(total)

    def detect_cost_anomaly(
        self, run_id: str, tenant_id: str, agent_id: str
    ) -> tuple[bool, str | None]:
        """Compara o custo total do run com a média das últimas execuções
        concluídas do mesmo agente/tenant. Sem histórico suficiente, não
        opina — silêncio é melhor que um falso alarme no primeiro run."""
        this_run_cost = self.total_cost_for_run(run_id)

        past_run_ids = self._session.execute(
            select(Run.id)
            .where(
                Run.tenant_id == tenant_id,
                Run.agent_id == agent_id,
                Run.status == RunStatus.DONE,
                Run.id != run_id,
            )
            .order_by(Run.created_at.desc())
            .limit(20)
        ).scalars().all()

        if len(past_run_ids) < ANOMALY_MIN_SAMPLES:
            return False, None

        past_costs = [
            self._session.execute(
                select(func.coalesce(func.sum(LedgerEntry.cost_usd), 0)).where(
                    LedgerEntry.run_id == rid
                )
            ).scalar_one()
            for rid in past_run_ids
        ]
        average = sum(float(c) for c in past_costs) / len(past_costs)

        if average > 0 and this_run_cost >= average * ANOMALY_MULTIPLIER:
            reason = (
                f"custou ${this_run_cost:.4f}, {this_run_cost / average:.1f}x a média "
                f"das últimas {len(past_run_ids)} execuções de '{agent_id}' (${average:.4f})"
            )
            return True, reason
        return False, None
