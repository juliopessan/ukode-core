from __future__ import annotations

from ukode_core.policy.engine import AgentPolicy, PolicyEngine


def _engine():
    policy = AgentPolicy.from_dict(
        "demo_agent",
        {
            "default_mode": "deny",
            "tools": [
                {"tool": "lookup_contact", "mode": "allow"},
                {
                    "tool": "send_whatsapp_message",
                    "mode": "approval",
                    "approvers": ["ops@ukodelabs.com"],
                    "max_calls_per_run": 2,
                },
                {"tool": "delete_all_data", "mode": "deny", "reason": "nunca permitido"},
            ],
        },
    )
    return PolicyEngine({"demo_agent": policy})


def test_allowed_tool_passes_straight_through():
    decision = _engine().evaluate("demo_agent", "lookup_contact", {})
    assert decision.allow
    assert not decision.needs_approval
    assert not decision.deny


def test_undeclared_tool_is_denied_by_default():
    decision = _engine().evaluate("demo_agent", "wire_transfer", {"amount": 1_000_000})
    assert decision.deny
    assert "não está autorizada" in decision.reason


def test_explicit_deny_reports_configured_reason():
    decision = _engine().evaluate("demo_agent", "delete_all_data", {})
    assert decision.deny
    assert decision.reason == "nunca permitido"


def test_approval_mode_returns_configured_approvers():
    decision = _engine().evaluate("demo_agent", "send_whatsapp_message", {"to": "x"})
    assert decision.needs_approval
    assert decision.approvers == ["ops@ukodelabs.com"]


def test_max_calls_per_run_is_enforced():
    engine = _engine()
    within_limit = engine.evaluate("demo_agent", "send_whatsapp_message", {}, calls_so_far=1)
    over_limit = engine.evaluate("demo_agent", "send_whatsapp_message", {}, calls_so_far=2)
    assert within_limit.needs_approval
    assert over_limit.deny
    assert "limite" in over_limit.reason


def test_unknown_agent_is_denied():
    decision = PolicyEngine({}).evaluate("ghost_agent", "anything", {})
    assert decision.deny
    assert "não tem política" in decision.reason
