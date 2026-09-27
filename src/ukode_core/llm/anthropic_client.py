"""Adaptador para a API da Anthropic."""

from __future__ import annotations

from typing import Any

import anthropic

from ukode_core.llm.base import LLMResponse, LLMUsage, ToolCallRequest, ToolSpec


class AnthropicClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-5", max_tokens: int = 4096):
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[ToolSpec], system: str = ""
    ) -> LLMResponse:
        anthropic_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]
        resp = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
            tools=anthropic_tools or anthropic.NOT_GIVEN,
            system=system or anthropic.NOT_GIVEN,
        )

        text = ""
        tool_calls: list[ToolCallRequest] = []
        for block in resp.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCallRequest(id=block.id, name=block.name, arguments=block.input)
                )

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
            raw=resp,
        )
