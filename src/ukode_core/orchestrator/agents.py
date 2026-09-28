"""Definição declarativa de agentes: prompt de sistema, modelo e ferramentas
permitidas. Carregado de YAML — trocar o comportamento de um agente não pede
deploy de código, só editar o arquivo (e, se for expandir permissões, editar
também a política correspondente em policy/policies/).

Cada agente também carrega metadados de registro — dono, status, versão,
descrição. Isso existe para responder uma pergunta organizacional, não
técnica: "que agentes existem, quem é dono de cada um, e qual está ativo?"
Sem isso, todo time acumula agentes que ninguém sabe quem publicou.

`evaluators` é um papel separado de `owner`: o dono opera e aprova; o
avaliador só observa e registra achados (ver `telemetry/findings.py`), sem
poder de bloquear nada. É uma lista porque nenhum avaliador é exclusivo —
o mesmo agente pode ter mais de um observador independente ao mesmo tempo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class AgentStatus:
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


@dataclass
class AgentDefinition:
    agent_id: str
    system_prompt: str
    model: str = "claude-sonnet-5"
    tool_names: list[str] = field(default_factory=list)
    max_steps: int = 8
    owner: str = ""
    status: str = AgentStatus.DRAFT
    version: str = "1"
    description: str = ""
    evaluators: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, agent_id: str, data: dict) -> AgentDefinition:
        return cls(
            agent_id=agent_id,
            system_prompt=data.get("system_prompt", ""),
            model=data.get("model", "claude-sonnet-5"),
            tool_names=data.get("tools", []),
            max_steps=data.get("max_steps", 8),
            owner=data.get("owner", ""),
            status=data.get("status", AgentStatus.DRAFT),
            version=str(data.get("version", "1")),
            description=data.get("description", ""),
            evaluators=data.get("evaluators", []),
        )


def load_agents(agents_dir: str | Path) -> dict[str, AgentDefinition]:
    agents_dir = Path(agents_dir)
    agents: dict[str, AgentDefinition] = {}
    for path in sorted(agents_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        agent_id = data.get("agent_id", path.stem)
        agents[agent_id] = AgentDefinition.from_dict(agent_id, data)
    return agents
