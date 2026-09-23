"""Interface de LLM independente de provedor. Trocar de fornecedor é trocar
o adaptador, não reescrever o orquestrador."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw: Any = None


class LLMClient(Protocol):
    model: str

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[ToolSpec]
    ) -> LLMResponse: ...
