"""O registro de execução responde as 8 perguntas canônicas de uma auditoria
de agente, sem precisar vasculhar o JSON de eventos soltos."""

from __future__ import annotations

from ukode_core.approvals.notifiers import ConsoleNotifier
from ukode_core.llm.base import LLMResponse, LLMUsage, ToolCallRequest
from ukode_core.llm.fake_client import FakeLLMClient
from ukode_core.orchestrator.engine import Engine
from ukode_core.telemetry.replay import build_execution_record


async def test_replay_answers_the_eight_canonical_questions(
    db_session, agents, policy_engine, mcp_gateway, whatsapp_connector
):
    llm = FakeLLMClient(
        script=[
            LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_1", name="lookup_contact", arguments={"email": "lead@example.com"}
                    )
                ],
                usage=LLMUsage(input_tokens=100, output_tokens=20),
            ),
            LLMResponse(text="Contato encontrado.", usage=LLMUsage(input_tokens=50, output_tokens=10)),
        ]
    )
    engine = Engine(
        db_session, agents, {"default": llm}, policy_engine, mcp_gateway
    ).with_approval_notifier(ConsoleNotifier())

    run = await engine.start_run("acme", "demo_agent", "Confirme a sessão do lead@example.com")
    record = build_execution_record(db_session, run, agents)

    assert record["run_id"] == run.id
    assert record["agent_id"] == "demo_agent"
    assert record["agent_owner"] == "ops@ukodelabs.com"
    assert record["agent_version"] == "1"
    assert record["model"] == "fake-model"
    assert record["prompt"] == "Confirme a sessão do lead@example.com"
    assert record["resources_accessed"] == ["lookup_contact"]
    assert len(record["policies_applied"]) == 1
    assert record["policies_applied"][0]["outcome"] == "allow"
    assert record["cost_usd"] == 0.0  # fake-model tem preço zero
    assert record["status"] == "done"
    assert record["result_text"] == "Contato encontrado."
    assert record["audit_chain_valid"] is True
    assert record["cost_anomaly"] is False


async def test_replay_counts_a_tool_executed_after_human_approval(
    db_session, agents, policy_engine, mcp_gateway, whatsapp_connector
):
    """Achado em produção: uma chamada aprovada por humano é executada em
    resume_run(), não em _process_pending_tool_calls() — se resources_accessed
    olhasse só PolicyDecision.outcome == 'allow', a ferramenta some do
    replay mesmo tendo sido de fato chamada com sucesso."""
    llm = FakeLLMClient(
        script=[
            LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_1",
                        name="send_whatsapp_message",
                        arguments={"to": "+5511999999999", "message": "Oi"},
                    )
                ],
                usage=LLMUsage(50, 10),
            ),
            LLMResponse(text="Enviado.", usage=LLMUsage(20, 5)),
        ]
    )
    engine = Engine(
        db_session, agents, {"default": llm}, policy_engine, mcp_gateway
    ).with_approval_notifier(ConsoleNotifier())

    run = await engine.start_run("acme", "demo_agent", "Confirme a sessão")
    run = await engine.resume_run(run.id, approved=True, decided_by="ops@ukodelabs.com")

    record = build_execution_record(db_session, run, agents)

    assert record["resources_accessed"] == ["send_whatsapp_message"]
