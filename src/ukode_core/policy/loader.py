"""Carrega as políticas de um diretório de arquivos YAML, um por agente."""

from __future__ import annotations

from pathlib import Path

import yaml

from ukode_core.policy.engine import AgentPolicy, PolicyEngine


def load_policies(policies_dir: str | Path) -> PolicyEngine:
    policies_dir = Path(policies_dir)
    policies: dict[str, AgentPolicy] = {}
    for path in sorted(policies_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        agent_id = data.get("agent_id", path.stem)
        policies[agent_id] = AgentPolicy.from_dict(agent_id, data)
    return PolicyEngine(policies)
