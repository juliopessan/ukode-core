from __future__ import annotations

from pydantic import BaseModel


class CreateRunRequest(BaseModel):
    tenant_id: str
    agent_id: str
    message: str


class RunOut(BaseModel):
    id: str
    tenant_id: str
    agent_id: str
    status: str
    result_text: str | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class DecideApprovalRequest(BaseModel):
    approved: bool
    decided_by: str


class AgentOut(BaseModel):
    agent_id: str
    owner: str
    status: str
    version: str
    description: str
    model: str
    tool_names: list[str]
    total_runs: int
    last_run_at: str | None
    total_cost_usd: float
    tenants: list[str]


class PolicyDecisionOut(BaseModel):
    tool_name: str
    tool_args: dict
    outcome: str
    reason: str
    created_at: str

    model_config = {"from_attributes": True}


class ExecutionRecordOut(BaseModel):
    """Responde as 8 perguntas canônicas de uma auditoria de execução de agente."""

    run_id: str
    agent_id: str
    agent_owner: str
    agent_version: str
    model: str
    prompt: str | None
    policies_applied: list[PolicyDecisionOut]
    resources_accessed: list[str]
    cost_usd: float
    status: str
    result_text: str | None
    cost_anomaly: bool
    cost_anomaly_reason: str | None
    audit_chain_valid: bool
