"""Teste de ponta a ponta: agente -> política -> aprovação -> MCP -> custo ->
auditoria. É o mesmo caminho que a sessão As-Is demonstra ao cliente."""

from __future__ import annotations

from ukode_core.approvals.notifiers import ConsoleNotifier
from ukode_core.llm.base import LLMResponse, LLMUsage, ToolCallRequest
from ukode_core.llm.fake_client import FakeLLMClient
from ukode_core.models import ApprovalStatus, LedgerEntry, RunStatus
from ukode_core.orchestrator.engine import Engine
from ukode_core.telemetry.audit import AuditLog


def _scripted_success():
    return FakeLLMClient(
        script=[
            LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_1", name="lookup_contact", arguments={"email": "lead@example.com"}
                    )
                ],
                usage=LLMUsage(input_tokens=100, output_tokens=20),
            ),
            LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_2",
                        name="send_whatsapp_message",
                        arguments={"to": "+5511999999999", "message": "Sessão As-Is confirmada!"},
                    )
                ],
                usage=LLMUsage(input_tokens=150, output_tokens=30),
            ),
            LLMResponse(text="Feito, contato notificado.", usage=LLMUsage(input_tokens=80, output_tokens=15)),
        ]
    )


async def test_flow_pauses_for_approval_then_completes(
    db_session, agents, policy_engine, mcp_gateway, whatsapp_connector
):
    llm = _scripted_success()
    engine = Engine(
        db_session, agents, {"default": llm}, policy_engine, mcp_gateway
    ).with_approval_notifier(ConsoleNotifier())

    run = await engine.start_run("acme", "demo_agent", "Confirme a sessão do lead@example.com")

    # 1ª ferramenta (lookup_contact) é permitida direto; a 2ª (WhatsApp) pausa o run.
    assert run.status == RunStatus.AWAITING_APPROVAL
    assert whatsapp_connector.sent == []

    approval = run.approvals[0]
    assert approval.tool_name == "send_whatsapp_message"
    assert approval.status == ApprovalStatus.PENDING
    assert approval.approvers == ["ops@ukodelabs.com"]

    run = await engine.resume_run(run.id, approved=True, decided_by="ops@ukodelabs.com")

    assert run.status == RunStatus.DONE
    assert run.result_text == "Feito, contato notificado."
    assert len(whatsapp_connector.sent) == 1
    assert whatsapp_connector.sent[0]["to"] == "+5511999999999"

    approval = db_session.get(type(approval), approval.id)
    assert approval.status == ApprovalStatus.APPROVED
    assert approval.decided_by == "ops@ukodelabs.com"

    # 06: cada chamada de modelo virou uma linha de custo
    entries = db_session.query(LedgerEntry).filter(LedgerEntry.run_id == run.id).all()
    assert len(entries) == 3
    assert all(e.model == "fake-model" for e in entries)

    # 05: a trilha de auditoria está íntegra
    assert AuditLog(db_session).verify_chain(run.id) is True


async def test_flow_rejected_approval_is_reported_to_the_model(
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
                usage=LLMUsage(50, 10),
            ),
            LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_2",
                        name="send_whatsapp_message",
                        arguments={"to": "+5511999999999", "message": "Oi"},
                    )
                ],
                usage=LLMUsage(50, 10),
            ),
            LLMResponse(text="Entendido, não vou enviar a mensagem.", usage=LLMUsage(40, 8)),
        ]
    )
    engine = Engine(
        db_session, agents, {"default": llm}, policy_engine, mcp_gateway
    ).with_approval_notifier(ConsoleNotifier())

    run = await engine.start_run("acme", "demo_agent", "Confirme a sessão")
    assert run.status == RunStatus.AWAITING_APPROVAL

    run = await engine.resume_run(run.id, approved=False, decided_by="ops@ukodelabs.com")

    assert run.status == RunStatus.DONE
    assert whatsapp_connector.sent == []  # nunca chegou a chamar o MCP
    # a última mensagem antes da resposta final contém o motivo da negação
    tool_result_message = run.messages[-2]
    contents = [b["content"] for b in tool_result_message["content"]]
    assert any("aprovação negada" in c for c in contents)


async def test_tool_not_declared_in_policy_is_denied_without_approval(
    db_session, agents, policy_engine, mcp_gateway
):
    llm = FakeLLMClient(
        script=[
            LLMResponse(
                tool_calls=[ToolCallRequest(id="call_1", name="delete_customer", arguments={"id": "123"})],
                usage=LLMUsage(10, 5),
            ),
            LLMResponse(text="Não posso fazer isso.", usage=LLMUsage(10, 5)),
        ]
    )
    engine = Engine(db_session, agents, {"default": llm}, policy_engine, mcp_gateway)

    run = await engine.start_run("acme", "demo_agent", "Apague o cliente 123")

    assert run.status == RunStatus.DONE  # nunca pausou — negação é imediata, sem humano envolvido
    assert run.approvals == []
