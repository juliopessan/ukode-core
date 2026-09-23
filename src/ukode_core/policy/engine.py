"""Motor de políticas: para cada chamada de ferramenta que um agente tenta
fazer, decide se ela é permitida direto, precisa de aprovação humana, ou é
negada. As regras vêm de YAML por agente — item 03 da camada UKode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Decision:
    allow: bool
    needs_approval: bool = False
    deny: bool = False
    reason: str = ""
    approvers: list[str] = field(default_factory=list)

    @staticmethod
    def allowed() -> Decision:
        return Decision(allow=True)

    @staticmethod
    def denied(reason: str) -> Decision:
        return Decision(allow=False, deny=True, reason=reason)

    @staticmethod
    def approval(reason: str, approvers: list[str]) -> Decision:
        return Decision(allow=False, needs_approval=True, reason=reason, approvers=approvers)


@dataclass
class ToolPolicy:
    tool: str
    mode: str = "allow"  # allow | deny | approval
    approvers: list[str] = field(default_factory=list)
    reason: str = ""
    max_calls_per_run: int | None = None


@dataclass
class AgentPolicy:
    agent_id: str
    default_mode: str = "deny"  # negação por padrão: só o que está declarado é permitido
    tools: dict[str, ToolPolicy] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, agent_id: str, data: dict[str, Any]) -> AgentPolicy:
        tools = {}
        for entry in data.get("tools", []):
            policy = ToolPolicy(
                tool=entry["tool"],
                mode=entry.get("mode", "allow"),
                approvers=entry.get("approvers", []),
                reason=entry.get("reason", ""),
                max_calls_per_run=entry.get("max_calls_per_run"),
            )
            tools[policy.tool] = policy
        return cls(
            agent_id=agent_id,
            default_mode=data.get("default_mode", "deny"),
            tools=tools,
        )


class PolicyEngine:
    def __init__(self, policies: dict[str, AgentPolicy]):
        self._policies = policies

    @property
    def agent_ids(self) -> list[str]:
        return list(self._policies.keys())

    def allowed_tool_names(self, agent_id: str) -> list[str]:
        policy = self._policies.get(agent_id)
        if not policy:
            return []
        return [p.tool for p in policy.tools.values() if p.mode != "deny"]

    def evaluate(
        self, agent_id: str, tool_name: str, tool_args: dict, calls_so_far: int = 0
    ) -> Decision:
        policy = self._policies.get(agent_id)
        if policy is None:
            return Decision.denied(f"agente '{agent_id}' não tem política cadastrada")

        tool_policy = policy.tools.get(tool_name)
        if tool_policy is None:
            if policy.default_mode == "allow":
                return Decision.allowed()
            return Decision.denied(
                f"ferramenta '{tool_name}' não está autorizada para o agente '{agent_id}'"
            )

        if tool_policy.max_calls_per_run is not None and calls_so_far >= tool_policy.max_calls_per_run:
            return Decision.denied(
                f"limite de {tool_policy.max_calls_per_run} chamadas a '{tool_name}' "
                "por execução atingido"
            )

        if tool_policy.mode == "deny":
            return Decision.denied(tool_policy.reason or f"'{tool_name}' está bloqueada por política")
        if tool_policy.mode == "approval":
            return Decision.approval(
                tool_policy.reason or f"chamada a '{tool_name}' exige aprovação",
                approvers=tool_policy.approvers,
            )
        return Decision.allowed()
