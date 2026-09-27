from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ukode_core.api.deps import build_engine, get_db
from ukode_core.api.schemas import CreateRunRequest, ExecutionRecordOut, RunOut
from ukode_core.config import settings
from ukode_core.ledger.service import BudgetExceeded
from ukode_core.models import Run
from ukode_core.orchestrator.agents import load_agents
from ukode_core.telemetry.replay import build_execution_record

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunOut)
async def create_run(body: CreateRunRequest, db: Session = Depends(get_db)) -> Run:
    engine = build_engine(db)
    try:
        run = await engine.start_run(body.tenant_id, body.agent_id, body.message)
    except BudgetExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return run


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run não encontrado")
    return run


@router.get("/{run_id}/replay", response_model=ExecutionRecordOut)
def replay_run(run_id: str, db: Session = Depends(get_db)) -> ExecutionRecordOut:
    """As 8 perguntas canônicas de uma auditoria, respondidas para este run."""
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run não encontrado")
    agents = load_agents(settings.agents_dir)
    record = build_execution_record(db, run, agents)
    return ExecutionRecordOut(**record)
