from __future__ import annotations

from ukode_core.ledger.pricing import cost_usd
from ukode_core.ledger.service import BudgetExceeded, LedgerService
from ukode_core.llm.base import LLMUsage
from ukode_core.models import BudgetLimit, Run, RunStatus


def _make_run(session, tenant_id="acme"):
    run = Run(tenant_id=tenant_id, agent_id="demo_agent", status=RunStatus.RUNNING, messages=[])
    session.add(run)
    session.flush()
    return run


def test_cost_calculation_matches_pricing_table():
    cost = cost_usd("claude-sonnet-5", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 3.0 + 15.0


def test_unknown_model_falls_back_to_default_price():
    cost = cost_usd("some-future-model", input_tokens=1_000_000, output_tokens=0)
    assert cost == 3.0  # DEFAULT_PRICE.input_per_million


def test_record_usage_creates_ledger_entry_with_correct_cost(db_session):
    run = _make_run(db_session)
    ledger = LedgerService(db_session)

    entry = ledger.record(
        run.id, run.tenant_id, run.agent_id, "claude-sonnet-5", LLMUsage(input_tokens=2000, output_tokens=500)
    )

    assert entry.input_tokens == 2000
    assert entry.output_tokens == 500
    expected = cost_usd("claude-sonnet-5", 2000, 500)
    assert float(entry.cost_usd) == round(expected, 6)


def test_budget_check_passes_when_no_limit_configured(db_session):
    LedgerService(db_session).check_budget("acme", "demo_agent")  # não levanta


def test_budget_check_raises_once_limit_is_reached(db_session):
    run = _make_run(db_session)
    ledger = LedgerService(db_session)
    db_session.add(BudgetLimit(tenant_id="acme", agent_id=None, period="monthly", limit_usd=0.01))
    db_session.flush()

    ledger.record(run.id, "acme", "demo_agent", "claude-opus-5-5", LLMUsage(10_000, 10_000))

    try:
        ledger.check_budget("acme", "demo_agent")
        raise AssertionError("deveria ter levantado BudgetExceeded")
    except BudgetExceeded as exc:
        assert exc.tenant_id == "acme"
        assert exc.spent >= exc.limit


def test_budget_is_isolated_per_tenant(db_session):
    run_acme = _make_run(db_session, tenant_id="acme")
    run_other = _make_run(db_session, tenant_id="other")
    ledger = LedgerService(db_session)
    db_session.add(BudgetLimit(tenant_id="acme", agent_id=None, period="monthly", limit_usd=0.01))
    db_session.flush()

    ledger.record(run_other.id, "other", "demo_agent", "claude-opus-5-5", LLMUsage(50_000, 50_000))
    ledger.check_budget("acme", "demo_agent")  # gasto de "other" não afeta "acme"

    ledger.record(run_acme.id, "acme", "demo_agent", "claude-opus-5-5", LLMUsage(50_000, 50_000))
    try:
        ledger.check_budget("acme", "demo_agent")
        raise AssertionError("deveria ter levantado BudgetExceeded")
    except BudgetExceeded:
        pass
