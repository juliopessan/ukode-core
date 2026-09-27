"""Modelos ORM. Todo o estado de execução vive aqui — o worker pode reiniciar
a qualquer momento e retomar de onde parou (ex.: aguardando aprovação)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ukode_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    DONE = "done"
    FAILED = "failed"
    DENIED = "denied"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Run(Base):
    """Uma execução de agente, do início ao fim (possivelmente com pausas)."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    agent_id: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(30), default=RunStatus.PENDING)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Estado de retomada: chamadas de ferramenta do lote atual ainda não
    # processadas, e os resultados das que já foram — usados para continuar
    # exatamente de onde parou depois que uma aprovação é decidida.
    pending_tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    pending_tool_results: Mapped[list] = mapped_column(JSON, default=list)
    tool_call_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    # FinOps: marcado quando o custo total do run destoa do histórico do
    # mesmo agente — "a execução que pareceu normal e custou mais".
    cost_anomaly: Mapped[bool] = mapped_column(default=False)
    cost_anomaly_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    approvals: Mapped[list[Approval]] = relationship(back_populates="run")
    ledger_entries: Mapped[list[LedgerEntry]] = relationship(back_populates="run")
    audit_entries: Mapped[list[AuditLogEntry]] = relationship(
        back_populates="run", order_by="AuditLogEntry.seq"
    )
    policy_decisions: Mapped[list[PolicyDecision]] = relationship(
        back_populates="run", order_by="PolicyDecision.created_at"
    )


class Approval(Base):
    """Um pedido de humano-no-circuito para uma chamada de ferramenta específica."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    tool_call_id: Mapped[str] = mapped_column(String(120))
    tool_name: Mapped[str] = mapped_column(String(120))
    tool_args: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
    approvers: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING)
    decided_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped[Run] = relationship(back_populates="approvals")


class LedgerEntry(Base):
    """Registro contábil de uso e custo — um por chamada de modelo."""

    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    agent_id: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(120))
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped[Run] = relationship(back_populates="ledger_entries")


class AuditLogEntry(Base):
    """Trilha de auditoria só de inserção, encadeada por hash (append-only)."""

    __tablename__ = "audit_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    seq: Mapped[int] = mapped_column()
    event_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped[Run] = relationship(back_populates="audit_entries")


class PolicyDecision(Base):
    """Um registro por avaliação de política — não um evento de log solto,
    mas uma linha consultável: 'quais políticas foram aplicadas nesse run?'
    é uma query direta nesta tabela, não uma busca em JSON de auditoria."""

    __tablename__ = "policy_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(120), index=True)
    tool_call_id: Mapped[str] = mapped_column(String(120))
    tool_name: Mapped[str] = mapped_column(String(120))
    tool_args: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome: Mapped[str] = mapped_column(String(20))  # allow | deny | approval
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped[Run] = relationship(back_populates="policy_decisions")


class BudgetLimit(Base):
    """Teto de gasto por tenant (+ opcionalmente por agente)."""

    __tablename__ = "budget_limits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    period: Mapped[str] = mapped_column(String(20), default="monthly")  # monthly | daily
    limit_usd: Mapped[float] = mapped_column(Numeric(12, 2))
