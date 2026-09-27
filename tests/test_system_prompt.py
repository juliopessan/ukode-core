"""O 'prompt' do agente (persona, instruções) precisa realmente chegar ao
modelo — não só existir no YAML. Sem este teste, `system_prompt` pode ficar
declarado e nunca ser usado sem que nada acuse."""

from __future__ import annotations

from ukode_core.approvals.notifiers import ConsoleNotifier
from ukode_core.llm.base import LLMResponse, LLMUsage
from ukode_core.llm.fake_client import FakeLLMClient
from ukode_core.orchestrator.engine import Engine


async def test_agent_system_prompt_reaches_the_model(
    db_session, agents, policy_engine, mcp_gateway
):
    llm = FakeLLMClient(script=[LLMResponse(text="ok", usage=LLMUsage(5, 5))])
    engine = Engine(
        db_session, agents, {"default": llm}, policy_engine, mcp_gateway
    ).with_approval_notifier(ConsoleNotifier())

    await engine.start_run("acme", "demo_agent", "oi")

    assert len(llm.systems) == 1
    assert llm.systems[0] == agents["demo_agent"].system_prompt
    assert llm.systems[0].strip() != ""  # o agente de demo declara um prompt não vazio
