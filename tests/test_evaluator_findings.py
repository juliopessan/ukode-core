"""Papel de avaliador independente: acesso amplo de leitura, um canal
formal para registrar achados, e nenhum poder de bloquear execução —
inspirado no modelo de 'embedded evaluation' (Anthropic/Accenture): um
observador separado de quem opera e de quem aprova."""

from __future__ import annotations

from ukode_core.models import FindingSeverity, Run, RunStatus
from ukode_core.telemetry.findings import FindingService


def _make_run(session, agent_id="demo_agent"):
    run = Run(tenant_id="acme", agent_id=agent_id, status=RunStatus.DONE, messages=[])
    session.add(run)
    session.flush()
    return run


def test_agent_definition_carries_evaluators_distinct_from_owner(agents):
    agent = agents["demo_agent"]
    assert agent.owner == "ops@ukodelabs.com"
    assert "auditoria@ukodelabs.com" in agent.evaluators
    assert agent.owner not in agent.evaluators  # papéis distintos


def test_finding_can_be_reported_without_a_run(db_session):
    findings = FindingService(db_session)
    record = findings.report(
        agent_id="demo_agent",
        finding="Padrão observado: agente pediu aprovação 5x na última semana para o mesmo destinatário.",
        reported_by="auditoria@ukodelabs.com",
        severity=FindingSeverity.MEDIUM,
    )
    assert record.run_id is None
    assert record.severity == FindingSeverity.MEDIUM


def test_finding_can_be_scoped_to_a_specific_run(db_session):
    run = _make_run(db_session)
    findings = FindingService(db_session)
    record = findings.report(
        agent_id="demo_agent",
        run_id=run.id,
        finding="Mensagem gerada continha um tom fora do esperado.",
        reported_by="auditoria@ukodelabs.com",
        severity=FindingSeverity.LOW,
    )
    assert record.run_id == run.id
    assert findings.for_run(run.id) == [record]


def test_for_agent_lists_findings_newest_first(db_session):
    findings = FindingService(db_session)
    f1 = findings.report("demo_agent", "primeiro achado", "auditoria@ukodelabs.com")
    f2 = findings.report("demo_agent", "segundo achado", "auditoria@ukodelabs.com")
    listed = findings.for_agent("demo_agent")
    assert listed[0].id == f2.id
    assert listed[1].id == f1.id
    assert f1.severity == FindingSeverity.INFO  # severidade padrão


def test_default_severity_is_info(db_session):
    findings = FindingService(db_session)
    record = findings.report("demo_agent", "observação de rotina", "auditoria@ukodelabs.com")
    assert record.severity == "info"


def _client_with_isolated_db(db_session):
    """A API real, ligada ao mesmo banco isolado que os outros testes usam —
    em vez do arquivo sqlite de configuração padrão."""
    from httpx import ASGITransport, AsyncClient

    from ukode_core.api.app import app
    from ukode_core.api.deps import get_db

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test"), app


async def test_api_rejects_finding_from_someone_not_listed_as_evaluator(db_session):
    client, app = _client_with_isolated_db(db_session)
    try:
        async with client:
            resp = await client.post(
                "/agents/demo_agent/findings",
                json={"finding": "tentativa não autorizada", "reported_by": "alguem@fora.com"},
            )
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_api_accepts_finding_from_a_declared_evaluator(db_session):
    client, app = _client_with_isolated_db(db_session)
    try:
        async with client:
            resp = await client.post(
                "/agents/demo_agent/findings",
                json={
                    "finding": "revisão periódica: nenhum problema encontrado",
                    "reported_by": "auditoria@ukodelabs.com",
                    "severity": "info",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["agent_id"] == "demo_agent"
            assert body["reported_by"] == "auditoria@ukodelabs.com"

            listed = await client.get("/agents/demo_agent/findings")
            assert listed.status_code == 200
            assert any(f["id"] == body["id"] for f in listed.json())
    finally:
        app.dependency_overrides.clear()
