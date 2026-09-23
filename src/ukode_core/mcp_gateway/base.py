"""Interface de conector MCP. A camada é cliente dos MCP servers dos sistemas
do cliente (ERP, CRM, WhatsApp) e servidor para os agentes que orquestra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ukode_core.llm.base import ToolSpec


@dataclass
class ToolResult:
    ok: bool
    output: Any = None
    error: str | None = None


class Connector(Protocol):
    """Um conector expõe um conjunto de ferramentas (tools) e sabe executá-las."""

    name: str

    def tools(self) -> list[ToolSpec]: ...

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult: ...
