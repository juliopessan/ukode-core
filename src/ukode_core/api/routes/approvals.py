from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ukode_core.api.deps import build_engine, get_db
from ukode_core.api.schemas import DecideApprovalRequest, RunOut
from ukode_core.models import Run

router = APIRouter(prefix="/runs", tags=["approvals"])


@router.post("/{run_id}/approval", response_model=RunOut)
async def decide_approval(
    run_id: str, body: DecideApprovalRequest, db: Session = Depends(get_db)
) -> Run:
    engine = build_engine(db)
    try:
        run = await engine.resume_run(run_id, body.approved, body.decided_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return run
