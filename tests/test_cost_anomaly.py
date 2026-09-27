"""FinOps: 'a execução que pareceu normal e custou mais'. Sem histórico
suficiente não opina; com histórico, compara contra a média."""

from __future__ import annotations

from ukode_core.ledger.service import ANOMALY_MIN_SAMPLES, LedgerService
from ukode_core.llm.base import LLMUsage
from ukode_core.models import Run, RunStatus


def _done_run_with_cost(session, ledger, tenant_id, agent_id, cost_via_tokens):
    run = Run(tenant_id=tenant_id, agent_id=agent_id, status=RunStatus.DONE, messages=[])
    session.add(run)
    session.flush()
    input_tokens, output_tokens = cost_via_tokens
    ledger.record(run.id, tenant_id, agent_id, "claude-sonnet-5", LLMUsage(input_tokens, output_tokens))
    return run


def test_no_anomaly_without_enough_history(db_session):
    ledger = LedgerService(db_session)
    for _ in range(ANOMALY_MIN_SAMPLES - 1):
        _done_run_with_cost(db_session, ledger, "acme", "demo_agent", (1000, 200))

    current = _done_run_with_cost(db_session, ledger, "acme", "demo_agent", (1_000_000, 1_000_000))
    anomaly, reason = ledger.detect_cost_anomaly(current.id, "acme", "demo_agent")

    assert anomaly is False
    assert reason is None


def test_flags_a_run_far_above_the_historical_average(db_session):
    ledger = LedgerService(db_session)
    for _ in range(ANOMALY_MIN_SAMPLES):
        _done_run_with_cost(db_session, ledger, "acme", "demo_agent", (1000, 200))

    expensive = _done_run_with_cost(db_session, ledger, "acme", "demo_agent", (1_000_000, 1_000_000))
    anomaly, reason = ledger.detect_cost_anomaly(expensive.id, "acme", "demo_agent")

    assert anomaly is True
    assert "x a média" in reason


def test_does_not_flag_a_run_close_to_the_average(db_session):
    ledger = LedgerService(db_session)
    for _ in range(ANOMALY_MIN_SAMPLES):
        _done_run_with_cost(db_session, ledger, "acme", "demo_agent", (1000, 200))

    typical = _done_run_with_cost(db_session, ledger, "acme", "demo_agent", (1100, 210))
    anomaly, reason = ledger.detect_cost_anomaly(typical.id, "acme", "demo_agent")

    assert anomaly is False
    assert reason is None


def test_anomaly_is_scoped_to_the_same_agent_and_tenant(db_session):
    ledger = LedgerService(db_session)
    for _ in range(ANOMALY_MIN_SAMPLES):
        _done_run_with_cost(db_session, ledger, "acme", "other_agent", (1_000_000, 1_000_000))

    current = _done_run_with_cost(db_session, ledger, "acme", "demo_agent", (1000, 200))
    anomaly, _ = ledger.detect_cost_anomaly(current.id, "acme", "demo_agent")

    assert anomaly is False  # o histórico caro é de outro agente, não conta
