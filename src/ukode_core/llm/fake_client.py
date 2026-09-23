"""Cliente de LLM roteirizado — usado em testes e na demo sem depender de uma
chave de API real. Devolve as respostas passadas em `script`, em ordem."""

from __future__ import annotations

from typing import Any

from ukode_core.llm.base import LLMResponse, LLMUsage, ToolSpec


class FakeLLMClient:
    model = "fake-model"

    def __init__(self, script: list[LLMResponse]):
        self._script = list(script)
        self.calls: list[list[dict[str, Any]]] = []

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[ToolSpec]
    ) -> LLMResponse:
        self.calls.append(messages)
        if not self._script:
            return LLMResponse(text="(fim do roteiro)", usage=LLMUsage(10, 1))
        return self._script.pop(0)
