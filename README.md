# ukode-core

## O problema que isso resolve

Um agente de IA sozinho, numa demo, impressiona todo mundo. O segundo agente
já é outra história: alguém tem que decidir quem ele pode acessar, quem
aprova o que ele faz, quanto ele pode gastar e como provar depois o que ele
fez. Na prática, cada time reconstrói essas quatro coisas do zero, agente após
agente — e é aí que os projetos de IA travam entre a POC e a produção.

A resposta óbvia do mercado é "adicione um framework de agentes". Só que
framework de agente resolve orquestração e empurra identidade, aprovação,
custo e auditoria para fora — exatamente as partes que travam o projeto. E
resolver isso com um orquestrador visual (n8n e afins) troca o problema de
lugar: agora a lógica de política e de aprovação vive em nós de um fluxograma
que ninguém versiona nem testa como código.

`ukode-core` é a camada que fica entre os agentes (Copilot Studio, agentes
próprios, agentes de terceiros) e os sistemas de negócio do cliente (ERP,
CRM, contratos, WhatsApp). Ela não é mais um agente — é a infraestrutura
compartilhada que faz o segundo agente não começar do zero.

## Como funciona

Cada chamada de ferramenta que um agente tenta fazer passa pelo mesmo
caminho, sempre:

```
agente → política (permitido? negado? precisa de aprovação?)
       → se precisa de aprovação: pausa o run, notifica quem decide, e espera
       → se permitido: chama o conector MCP do sistema de negócio
       → registra o custo da chamada de modelo
       → grava um registro de auditoria encadeado por hash
```

O estado de cada execução (`Run`) vive inteiro no Postgres — inclusive quando
ela está pausada esperando um humano aprovar algo. Isso pode levar minutos ou
dias; quando a aprovação chega, a execução retoma exatamente de onde parou,
mesmo que o processo que a criou já tenha reiniciado.

Não há framework de agente, não há fila externa (Redis/Celery/RabbitMQ) e não
há orquestrador visual. Orquestração é um laço em `orchestrator/engine.py`;
fila é uma tabela no Postgres consumida com `SELECT ... FOR UPDATE SKIP
LOCKED`; política é YAML lido por um motor de ~100 linhas. O que é
protocolo padrão (chamar um LLM, falar MCP, emitir telemetria OpenTelemetry,
validar um token OIDC) usa a biblioteca oficial. O que é o produto —
orquestração, política, aprovação, custo, auditoria — é código Python seu,
que o cliente recebe pronto para operar.

## Estrutura

```
src/ukode_core/
├── api/            # FastAPI: criar runs, decidir aprovações, saúde
├── worker/         # consome runs pendentes do Postgres (fila durável)
├── orchestrator/   # o motor: Run, agentes declarados em YAML, o laço central
├── llm/            # interface de LLM + adaptador Anthropic + cliente roteirizado p/ testes
├── mcp_gateway/     # registro de conectores MCP + conectores de demonstração
├── policy/         # motor de políticas + políticas YAML por agente
├── approvals/      # pedidos de aprovação + canais de notificação
├── ledger/         # preço por modelo, uso, orçamento por tenant/agente
└── telemetry/      # OpenTelemetry + auditoria append-only encadeada por hash

site/               # landing da UKode Labs + peças de arquitetura + viewer ao vivo
├── index.html
├── camadas-backend.html    # Orchestrator vs Policy Engine vs Audit & Replay
├── camadas-frontend.html   # por que não há builder visual nem dashboard
├── camadas-infra.html      # Traefik + Postgres reaproveitados, api/worker novos
└── live.html               # acompanha um run real, em tempo real, no navegador
```

## Governança que responde perguntas, não só grava logs

- **Registro de agentes** (`GET /agents`) — todo agente declara dono, status,
  versão e descrição no YAML. O endpoint soma isso a fatos ao vivo: quantos
  runs, quando foi o último, quanto já custou, em quais tenants roda. Nenhum
  agente sem dono.
- **Replay de execução** (`GET /runs/{id}/replay`) — responde, para qualquer
  run: qual agente, quem é o dono, qual versão, qual modelo, qual prompt,
  quais políticas foram aplicadas, quais recursos foram acessados, quanto
  custou, e se a trilha de auditoria continua íntegra.
- **Decisões de política persistidas** — cada avaliação (permitir, negar,
  pedir aprovação) vira uma linha em `policy_decisions`, consultável direto.
- **Custo anômalo** — ao terminar, o run é comparado com a média das últimas
  execuções do mesmo agente e tenant; se custou 3x ou mais, fica marcado com
  o motivo. Sem histórico mínimo (5 runs), não opina.

## Demonstração ao vivo

O projeto está publicado na VPS do lab, com Postgres dedicado, HTTPS e o
modelo real da Anthropic — nada roteirizado:

- **Landing:** https://ukodelabs.srv1774174.hstgr.cloud
- **API:** https://ukode-core.srv1774174.hstgr.cloud
- **Acompanhar um run em tempo real:** https://ukodelabs.srv1774174.hstgr.cloud/live.html
  — clica em "rodar demonstração" e vê o agente decidir, pedir aprovação e ser
  auditado ao vivo, sondando `GET /runs/{id}/replay` a cada 900ms.

A API não tem UI própria por decisão (ver `camadas-frontend.html`), então o
CORS vem liberado (`allow_origins=["*"]`) em `api/app.py` — sem isso nenhuma
página estática consegue chamá-la do navegador. Um tenant real trocaria isso
por uma lista explícita de origens.

Deploy de referência em [deploy/docker-compose.prod.yml](deploy/docker-compose.prod.yml):
reaproveita o Traefik (que roda em `network_mode: host` no lab, então não
precisa de rede externa nenhuma) e um Postgres compartilhado, com role e
banco dedicados para este projeto — nunca a credencial de admin do Postgres.

## Rodando localmente

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                       # roda tudo em SQLite em memória, sem serviço externo
uvicorn ukode_core.api.app:app --reload   # sobe a API (usa SQLite local por padrão)
```

Sem `ANTHROPIC_API_KEY` configurada, a API cai automaticamente para um
cliente de LLM roteirizado — dá para explorar o fluxo de políticas e
aprovações sem nenhum segredo configurado. Copie `.env.example` para `.env`
para apontar para um Postgres de verdade e uma chave real.

### Exemplo: criar um run e aprovar manualmente

```bash
curl -X POST localhost:8000/runs -H 'content-type: application/json' -d '{
  "tenant_id": "acme",
  "agent_id": "demo_agent",
  "message": "Confirme a sessão do lead@example.com"
}'
# -> status "awaiting_approval": o agente quer enviar WhatsApp e a política exige aprovação

curl -X POST localhost:8000/runs/<run_id>/approval -H 'content-type: application/json' -d '{
  "approved": true,
  "decided_by": "ops@ukodelabs.com"
}'
# -> status "done": a mensagem foi enviada, o custo e a auditoria já foram gravados
```

## Adicionando um agente novo

1. Declare o agente em `orchestrator/agents/<nome>.yaml` (prompt, modelo, ferramentas).
2. Declare a política correspondente em `policy/policies/<nome>.yaml` — por padrão,
   toda ferramenta não listada é negada (`default_mode: deny`).
3. Se o agente precisa de um sistema novo (outro CRM, outro ERP), implemente um
   `Connector` em `mcp_gateway/` e registre-o em `api/deps.py::build_mcp_gateway`.
   Em produção, o conector fala com o MCP server real do sistema; a interface é
   a mesma usada pelos conectores de demonstração.

Nenhum desses três passos pede mudar `orchestrator/engine.py`.

## Do lab para o cliente

Em desenvolvimento e nas demos (sessão As-Is), `ukode-core` roda em dois
containers (`api` + `worker`) sobre um Postgres compartilhado. Em produção no
ambiente do cliente, a mesma imagem sobe no ambiente dele — Azure Container
Apps, AKS, ou onde já estiver rodando Copilot Studio — com um Postgres
dedicado e identidade validada contra o Entra ID (ou o provedor OIDC que o
cliente já usa). O código não muda entre os dois cenários; muda a
configuração.
