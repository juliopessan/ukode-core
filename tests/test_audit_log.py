from __future__ import annotations

from ukode_core.models import Run, RunStatus
from ukode_core.telemetry.audit import AuditLog


def _make_run(session):
    run = Run(tenant_id="acme", agent_id="demo_agent", status=RunStatus.RUNNING, messages=[])
    session.add(run)
    session.flush()
    return run


def test_chain_is_valid_after_normal_appends(db_session):
    run = _make_run(db_session)
    audit = AuditLog(db_session)
    audit.append(run.id, "run_started", {"a": 1})
    audit.append(run.id, "llm_call", {"tokens": 100})
    audit.append(run.id, "run_finished", {"text": "ok"})

    assert audit.verify_chain(run.id) is True


def test_chain_breaks_if_a_payload_is_tampered_with(db_session):
    run = _make_run(db_session)
    audit = AuditLog(db_session)
    audit.append(run.id, "run_started", {"a": 1})
    entry = audit.append(run.id, "llm_call", {"tokens": 100})
    audit.append(run.id, "run_finished", {"text": "ok"})

    entry.payload = {"tokens": 999999}  # alguém editou um registro "antigo"
    db_session.flush()

    assert audit.verify_chain(run.id) is False


def test_each_run_has_its_own_independent_chain(db_session):
    run_a = _make_run(db_session)
    run_b = _make_run(db_session)
    audit = AuditLog(db_session)
    audit.append(run_a.id, "run_started", {})
    audit.append(run_b.id, "run_started", {})

    assert audit.verify_chain(run_a.id) is True
    assert audit.verify_chain(run_b.id) is True
