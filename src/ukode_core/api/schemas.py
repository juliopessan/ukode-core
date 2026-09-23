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
