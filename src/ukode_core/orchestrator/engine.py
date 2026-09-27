"""O orquestrador. Sem framework de agente: um loop simples, com todo o
estado no Postgres, capaz de pausar por dias (aguardando aprovação humana) e
retomar exatamente de onde parou, mesmo depois de o worker reiniciar.

Ordem de cada passo, por chamada de ferramenta que o modelo pede:
  1. checar orçamento (ledger)          — 06
  2. chamar o modelo                    — registra uso e auditoria
  3. para cada tool_use: avaliar política — 03
       negado      -> resultado de erro, segue
       aprovação   -> pausa o run inteiro, notifica quem aprova — 04
       permitido   -> chama o conector MCP — 02, registra auditoria — 05
  4. quando não sobra tool_use: termina o run
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ukode_core.approvals.service import ApprovalService
from ukode_core.ledger.service import LedgerService
from ukode_core.llm.base import LLMClient, ToolCallRequest
from ukode_core.mcp_gateway.registry import MCPGateway
from ukode_core.models import PolicyDecision, Run, RunStatus
from ukode_core.orchestrator.agents import AgentDefinition
from ukode_core.orchestrator.messages import (
    assistant_message,
    denied_block,
    tool_result_block,
    user_tool_results_message,
)
from ukode_core.policy.engine import PolicyEngine
from ukode_core.telemetry.audit import AuditLog


class Engine:
    def __init__(
        self,
        session: Session,
        agents: dict[str, AgentDefinition],
        llm_clients: dict[str, LLMClient],
        policy_engine: PolicyEngine,
        mcp_gateway: MCPGateway,
    ):
        self._session = session
        self._agents = agents
        self._llm_clients = llm_clients
        self._policy = policy_engine
        self._mcp = mcp_gateway
        self._approvals = ApprovalService(session, notifier=_null_notifier())
        self._ledger = LedgerService(session)
        self._audit = AuditLog(session)

    def with_approval_notifier(self, notifier) -> Engine:
        self._approvals = ApprovalService(self._session, notifier=notifier)
        return self

    def _record_policy_decision(
        self, run: Run, agent_id: str, call_dict: dict, outcome: str, reason: str
    ) -> None:
        self._session.add(
            PolicyDecision(
                run_id=run.id,
                agent_id=agent_id,
                tool_call_id=call_dict["id"],
                tool_name=call_dict["name"],
                tool_args=call_dict["arguments"],
                outcome=outcome,
                reason=reason,
            )
        )
        self._session.flush()

    # -- ciclo de vida -----------------------------------------------------

    async def start_run(self, tenant_id: str, agent_id: str, user_message: str) -> Run:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"agente desconhecido: {agent_id}")

        run = Run(
            tenant_id=tenant_id,
            agent_id=agent_id,
            status=RunStatus.RUNNING,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_message}]}],
        )
        self._session.add(run)
        self._session.flush()
        self._audit.append(run.id, "run_started", {"tenant_id": tenant_id, "agent_id": agent_id})

        return await self._advance(run, agent)

    async def resume_run(self, run_id: str, approved: bool, decided_by: str) -> Run:
        run = self._session.get(Run, run_id)
        if run is None:
            raise ValueError(f"run não encontrado: {run_id}")
        if run.status != RunStatus.AWAITING_APPROVAL:
            raise ValueError(f"run {run_id} não está aguardando aprovação (status={run.status})")

        approval = self._approvals.latest_pending_for_run(run_id)
        if approval is None:
            raise ValueError(f"nenhuma aprovação pendente para o run {run_id}")
        self._approvals.decide(approval.id, approved, decided_by)

        agent = self._agents[run.agent_id]

        # resolve a chamada que estava pausada
        pending = list(run.pending_tool_calls)
        call_dict = pending.pop(0)  # a que gerou a aprovação é sempre a primeira da fila
        call = ToolCallRequest(id=call_dict["id"], name=call_dict["name"], arguments=call_dict["arguments"])

        results = list(run.pending_tool_results)
        if approved:
            result = await self._mcp.call(call.name, call.arguments)
            self._audit.append(
                run.id, "tool_call", {"tool": call.name, "args": call.arguments, "ok": result.ok}
            )
            results.append(tool_result_block(call.id, result))
        else:
            self._audit.append(run.id, "tool_call_rejected", {"tool": call.name, "args": call.arguments})
            results.append(denied_block(call.id, "aprovação negada por humano"))

        run.pending_tool_calls = pending
        run.pending_tool_results = results
        run.status = RunStatus.RUNNING
        self._session.flush()

        return await self._process_pending_tool_calls(run, agent)

    # -- núcleo --------------------------------------------------------

    async def _advance(self, run: Run, agent: AgentDefinition) -> Run:
        self._ledger.check_budget(run.tenant_id, agent.agent_id)

        llm = self._llm_clients.get(agent.model) or self._llm_clients["default"]
        tools = self._mcp.tools_for(agent.tool_names)

        response = await llm.complete(run.messages, tools, system=agent.system_prompt)
        self._ledger.record(run.id, run.tenant_id, agent.agent_id, llm.model, response.usage)
        self._audit.append(
            run.id,
            "llm_call",
            {"model": llm.model, "input_tokens": response.usage.input_tokens,
             "output_tokens": response.usage.output_tokens, "tool_calls": len(response.tool_calls)},
        )

        run.messages = [*run.messages, assistant_message(response)]

        if not response.tool_calls:
            run.status = RunStatus.DONE
            run.result_text = response.text
            anomaly, reason = self._ledger.detect_cost_anomaly(
                run.id, run.tenant_id, agent.agent_id
            )
            run.cost_anomaly = anomaly
            run.cost_anomaly_reason = reason
            self._audit.append(
                run.id, "run_finished", {"text": response.text, "cost_anomaly": anomaly}
            )
            self._session.flush()
            return run

        run.pending_tool_calls = [
            {"id": c.id, "name": c.name, "arguments": c.arguments} for c in response.tool_calls
        ]
        run.pending_tool_results = []
        self._session.flush()

        return await self._process_pending_tool_calls(run, agent)

    async def _process_pending_tool_calls(self, run: Run, agent: AgentDefinition) -> Run:
        counts: dict[str, int] = dict(run.tool_call_counts)

        while run.pending_tool_calls:
            call_dict = run.pending_tool_calls[0]
            tool_name = call_dict["name"]
            tool_args = call_dict["arguments"]

            decision = self._policy.evaluate(
                agent.agent_id, tool_name, tool_args, calls_so_far=counts.get(tool_name, 0)
            )

            if decision.deny:
                self._record_policy_decision(run, agent.agent_id, call_dict, "deny", decision.reason)
                self._audit.append(
                    run.id,
                    "tool_call_denied",
                    {"tool": tool_name, "args": tool_args, "reason": decision.reason},
                )
                run.pending_tool_results = [
                    *run.pending_tool_results,
                    denied_block(call_dict["id"], decision.reason),
                ]
                run.pending_tool_calls = run.pending_tool_calls[1:]
                self._session.flush()
                continue

            if decision.needs_approval:
                self._record_policy_decision(
                    run, agent.agent_id, call_dict, "approval", decision.reason
                )
                run.status = RunStatus.AWAITING_APPROVAL
                self._session.flush()
                await self._approvals.request(
                    run.id, call_dict["id"], tool_name, tool_args, decision.reason, decision.approvers
                )
                self._audit.append(
                    run.id, "approval_requested", {"tool": tool_name, "args": tool_args}
                )
                self._session.flush()
                return run  # pausa aqui; retoma via resume_run()

            self._record_policy_decision(run, agent.agent_id, call_dict, "allow", "")
            result = await self._mcp.call(tool_name, tool_args)
            self._audit.append(
                run.id, "tool_call", {"tool": tool_name, "args": tool_args, "ok": result.ok}
            )
            counts[tool_name] = counts.get(tool_name, 0) + 1
            run.pending_tool_results = [
                *run.pending_tool_results,
                tool_result_block(call_dict["id"], result),
            ]
            run.pending_tool_calls = run.pending_tool_calls[1:]
            self._session.flush()

        run.tool_call_counts = counts
        run.messages = [*run.messages, user_tool_results_message(run.pending_tool_results)]
        run.pending_tool_results = []
        self._session.flush()

        return await self._advance(run, agent)


def _null_notifier():
    from ukode_core.approvals.notifiers import ConsoleNotifier

    return ConsoleNotifier()
