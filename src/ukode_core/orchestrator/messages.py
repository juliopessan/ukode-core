"""Conversão entre `LLMResponse`/`ToolResult` e o formato de mensagens
persistido no `Run` (compatível com o formato de conteúdo da Anthropic:
blocos `text`, `tool_use` e `tool_result`)."""

from __future__ import annotations

from typing import Any

from ukode_core.llm.base import LLMResponse
from ukode_core.mcp_gateway.base import ToolResult


def assistant_message(response: LLMResponse) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    if response.text:
        content.append({"type": "text", "text": response.text})
    for call in response.tool_calls:
        content.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
    return {"role": "assistant", "content": content}


def tool_result_block(tool_call_id: str, result: ToolResult) -> dict[str, Any]:
    if result.ok:
        return {"type": "tool_result", "tool_use_id": tool_call_id, "content": str(result.output)}
    return {
        "type": "tool_result",
        "tool_use_id": tool_call_id,
        "content": result.error or "erro desconhecido",
        "is_error": True,
    }


def denied_block(tool_call_id: str, reason: str) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_call_id,
        "content": f"chamada negada pela política: {reason}",
        "is_error": True,
    }


def user_tool_results_message(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    return {"role": "user", "content": blocks}
