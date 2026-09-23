"""Serviço de aprovações: cria o pedido, notifica, e resolve a decisão.
O `Run` fica pausado em `awaiting_approval` até alguém decidir — mesmo que
isso leve dias, mesmo que o worker reinicie no meio do caminho."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ukode_core.approvals.notifiers import Notifier
from ukode_core.models import Approval, ApprovalStatus


class ApprovalService:
    def __init__(self, session: Session, notifier: Notifier):
        self._session = session
        self._notifier = notifier

    async def request(
        self,
        run_id: str,
        tool_call_id: str,
        tool_name: str,
        tool_args: dict,
        reason: str,
        approvers: list[str],
    ) -> Approval:
        approval = Approval(
            run_id=run_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_args=tool_args,
            reason=reason,
            approvers=approvers,
            status=ApprovalStatus.PENDING,
        )
        self._session.add(approval)
        self._session.flush()

        summary = f"{tool_name}({tool_args}) — {reason}"
        await self._notifier.notify(approval.id, approvers, summary)
        return approval

    def decide(self, approval_id: str, approved: bool, decided_by: str) -> Approval:
        approval = self._session.get(Approval, approval_id)
        if approval is None:
            raise ValueError(f"aprovação não encontrada: {approval_id}")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"aprovação {approval_id} já foi decidida ({approval.status})")

        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        approval.decided_by = decided_by
        approval.decided_at = datetime.now(UTC).replace(tzinfo=None)
        self._session.flush()
        return approval

    def latest_pending_for_run(self, run_id: str) -> Approval | None:
        return (
            self._session.query(Approval)
            .filter(Approval.run_id == run_id, Approval.status == ApprovalStatus.PENDING)
            .order_by(Approval.created_at.desc())
            .first()
        )
