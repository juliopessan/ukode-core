"""Conectores de demonstração, em memória — sem depender de um MCP server
real (Evolution API, CRM, ERP) para rodar a demo ou os testes. A interface é
a mesma que um conector real usaria; trocar a implementação por uma que fala
com um MCP server de verdade não muda o resto da camada."""

from __future__ import annotations

from typing import Any

from ukode_core.llm.base import ToolSpec
from ukode_core.mcp_gateway.base import ToolResult


class WhatsAppDemoConnector:
    name = "whatsapp"

    def __init__(self):
        self.sent: list[dict[str, Any]] = []

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="send_whatsapp_message",
                description="Envia uma mensagem de WhatsApp para um número de telefone.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["to", "message"],
                },
            )
        ]

    async def call(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name != "send_whatsapp_message":
            return ToolResult(ok=False, error=f"ferramenta desconhecida: {tool_name}")
        self.sent.append(arguments)
        return ToolResult(ok=True, output={"status": "sent", "to": arguments["to"]})


class CRMDemoConnector:
    name = "crm"

    def __init__(self, contacts: dict[str, dict] | None = None):
        self._contacts = contacts or {}

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="lookup_contact",
                description="Busca um contato do CRM pelo e-mail.",
                input_schema={
                    "type": "object",
                    "properties": {"email": {"type": "string"}},
                    "required": ["email"],
                },
            )
        ]

    async def call(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name != "lookup_contact":
            return ToolResult(ok=False, error=f"ferramenta desconhecida: {tool_name}")
        contact = self._contacts.get(arguments["email"])
        if not contact:
            return ToolResult(ok=False, error="contato não encontrado")
        return ToolResult(ok=True, output=contact)
