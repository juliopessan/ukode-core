"""Canais de notificação para pedidos de aprovação. Item 04 da camada UKode:
aprovação exatamente onde está o risco, avisando quem precisa decidir."""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class Notifier(Protocol):
    async def notify(self, approval_id: str, approvers: list[str], summary: str) -> None: ...


class ConsoleNotifier:
    """Usado no lab e nos testes — imprime o pedido em vez de enviar de verdade."""

    def __init__(self):
        self.sent: list[dict[str, Any]] = []

    async def notify(self, approval_id: str, approvers: list[str], summary: str) -> None:
        entry = {"approval_id": approval_id, "approvers": approvers, "summary": summary}
        self.sent.append(entry)
        print(f"[aprovação pendente] {approval_id} → {approvers}: {summary}")


class WebhookNotifier:
    """Dispara um webhook (ex.: rota que envia por WhatsApp via Evolution API,
    ou por Teams/e-mail no ambiente do cliente)."""

    def __init__(self, url: str):
        self._url = url

    async def notify(self, approval_id: str, approvers: list[str], summary: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                self._url,
                json={"approval_id": approval_id, "approvers": approvers, "summary": summary},
            )
