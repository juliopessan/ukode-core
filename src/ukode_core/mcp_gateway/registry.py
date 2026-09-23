"""Registro central de conectores MCP disponíveis para os agentes.

Constrói o conector uma vez; todo agente autorizado usa (item 02 da camada
UKode). Em produção, cada `Connector` real fala com um MCP server verdadeiro
(via `mcp` SDK) apontando para o ERP/CRM/WhatsApp do cliente; aqui o registro
não sabe nem precisa saber disso — ele só roteia por nome de ferramenta."""

from __future__ import annotations

from ukode_core.llm.base import ToolSpec
from ukode_core.mcp_gateway.base import Connector, ToolResult


class ConnectorNotFound(Exception):
    pass


class MCPGateway:
    def __init__(self, connectors: list[Connector]):
        self._connectors = {c.name: c for c in connectors}
        self._tool_index: dict[str, str] = {}
        for connector in connectors:
            for tool in connector.tools():
                self._tool_index[tool.name] = connector.name

    def tools_for(self, tool_names: list[str]) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        for connector in self._connectors.values():
            for tool in connector.tools():
                if tool.name in tool_names:
                    specs.append(tool)
        return specs

    async def call(self, tool_name: str, arguments: dict) -> ToolResult:
        connector_name = self._tool_index.get(tool_name)
        if connector_name is None:
            return ToolResult(ok=False, error=f"ferramenta desconhecida: {tool_name}")
        connector = self._connectors[connector_name]
        try:
            return await connector.call(tool_name, arguments)
        except Exception as exc:  # noqa: BLE001 — queremos reportar qualquer falha ao run
            return ToolResult(ok=False, error=str(exc))
