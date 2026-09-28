# Brag Plan: ukode-core

## What is this app?
A camada de orquestração de agentes da UKode Labs: toda ação que um agente de IA tenta fazer passa por uma política avaliada fora dele, pede aprovação humana quando há risco, registra o custo e grava uma trilha de auditoria que responde oito perguntas. Python puro, sem framework de agente, rodando ao vivo com o Claude real.

## The angle
O agente não é o herói; o **freio** é. Todo mundo mostra o agente fazendo coisas. Nós mostramos o agente **parando** para pedir permissão, um humano decidindo, e a execução voltando de onde parou, com o recibo completo no fim. A graça séria: o momento mais impressionante do produto é uma pausa.

## Hook (first 2-3 seconds)
Num console escuro, uma chamada real aparece digitada: `send_whatsapp_message(to: "+55 11 9····")`. Antes de terminar, um carimbo clay cai por cima: **PRECISA DE APROVAÇÃO**. A frase acima: "Seu agente quer agir."

## Key moments (the middle)
- As linhas do console chegando uma a uma, como na página ao vivo: `pedido` → `lookup_contact — permitido` (mint) → `send_whatsapp_message — precisa de aprovação` (clay).
- A caixa de aprovação surge; um cursor clica em "Aprovar". O ponto de status muda de clay pulsando para mint: "concluído".
- O replay preenchendo as oito perguntas linha a linha, terminando em "Auditoria íntegra? sim, verificada" em mint e o custo real `$0.013743`.

## Outro / punchline
"Sem n8n. Sem LangChain. Sem framework de agente." (riscados um a um) → "ukode-core" grande, com a linha de voz serif: "*o humano decide.*" → "UKode Labs".

## User flow worth showing
Pedido em linguagem natural → a política pausa a ação arriscada e pede aprovação → humano aprova, a execução termina e o replay responde as oito perguntas com o custo real. Material vem de `site/live.html` e de um run real no ar (run `beca3f65`, modelo `claude-sonnet-5`, custo `$0.013743`, recursos `lookup_contact, send_whatsapp_message`).

## Tone
- Preset: polished
- Creative direction: "o livro-razão como protagonista": filme de produto silencioso e confiante, no sistema Ledger
- Interpretation: poucas cenas, holds longos, movimento contido; tipografia faz o trabalho; o único "efeito" é o carimbo e a troca clay → mint.

## Format: landscape — 1920x1080
## Duration: 22s

## Visual identity (from the project)
- Background: #f2efe8 (paper), inset #14140f (ledger), superfície #e7e3da
- Accent: clay #ed6738 / #c8481c = pendente/não verificado; mint #4f9c6b / #8fcfa6 = verificado. **Reservados**: só com esse significado.
- Text: #11110f (ink), #55524b (soft), #8a867c (faint)
- Display font: Archivo 800
- Body font: IBM Plex Mono (instrumento) + Instrument Serif itálico uma única vez (voz)
- Strongest visual element: o console escuro de `live.html` e o painel "replay · 8 perguntas"

## Privacidade
Sem hostnames da VPS, sem e-mails, sem chaves. Aprovador aparece como "ops". Telefone mascarado (`+55 11 9····`). O contato é o fictício "Lead de Exemplo".

## Share copy (draft)
O momento mais impressionante do nosso agente é quando ele para. Política fora do agente, aprovação humana, custo e auditoria de 8 perguntas, em Python puro, sem LangChain, rodando ao vivo.

## Audio direction
- Role: sparse professional accents over a warm, low bed
- Music: happy-beats-business-moves-vol-11 (114.84 BPM), baixo no mix
- Music treatment: fade-in curto desde 0s, bed discreto, fade-out nos 1.5s finais
- Music cue guidance: preset lido. Strong cues em 1.60s, 3.70s, 5.80s, 8.96s, 12.65s, 17.91s. Alvos: carimbo do hook ≈1.60s; revelação do nome ≈3.70s; clique em "Aprovar" ≈12.65s; última linha "sim, verificada" ≈17.91s. Beat grid ~0.52s para as linhas do console e do replay.
- Audio-reactive treatment: none (tom polished)
- SFX posture: sparse, motion-matched
- Audio-coupled moments: teclado discreto no typing do hook; um impacto seco no carimbo; tick suave por linha do console; clique de UI no "Aprovar"; tick leve por linha do replay
- Restraint rule: nada de whoosh em toda transição; efeitos sempre abaixo da música

## Storyboard

### Scene 1 — Hook: o agente quer agir — 3.5s
Console escuro no centro. Acima, em Archivo: "Seu agente quer agir." A chamada `send_whatsapp_message(to: "+55 11 9····", message: "Sessão confirmada")` é digitada. Carimbo clay "PRECISA DE APROVAÇÃO" cai rotacionado.
Sequential/interaction: yes — digitação caractere a caractere, depois o carimbo
Audio intent: tensão contida
Audio-coupled idea: key ticks na digitação; impacto seco no carimbo
Music: entra baixa
Transition mood: soft → Scene 2

### Scene 2 — Reveal — 3.5s
Papel claro. "ukode-core" em Archivo grande; abaixo, em mono: "política antes da ação · aprovação humana · custo · auditoria". Eyebrow: "UKode Labs".
Sequential/interaction: os quatro termos entram um a um
Audio intent: confiança
Audio-coupled idea: tick leve por termo
Transition mood: soft → Scene 3

### Scene 3 — O fluxo ao vivo — 6.5s
Recriação fiel de `live.html`: o console com cabeçalho "run · demo_agent · beca3f65". Linhas chegam uma a uma: `pedido "Confirme a sessão do lead@example.com"`, `política lookup_contact — permitido` (mint), `política send_whatsapp_message — precisa de aprovação` (clay). Status "aguardando aprovação humana" com ponto clay pulsando. A caixa de aprovação aparece; o cursor vai até "Aprovar" e clica; linha `humano aprovou — ops`; status vira "concluído" com ponto mint.
Sequential/interaction: yes — linhas uma a uma, clique simulado
Audio intent: o produto trabalhando
Audio-coupled idea: tick por linha; clique de UI no Aprovar
Transition mood: soft → Scene 4

### Scene 4 — O recibo: oito perguntas — 5s
O painel escuro "replay · 8 perguntas" com o custo `$0.013743` no canto. As linhas preenchem uma a uma: Qual agente? demo_agent · Quem é o dono? ops · Qual versão? 1 · Qual modelo? claude-sonnet-5 · Políticas aplicadas? 2 decisões · Recursos acessados? lookup_contact, send_whatsapp_message · Quanto custou? $0.013743 · Auditoria íntegra? **sim, verificada** (mint).
Sequential/interaction: yes — oito linhas em sequência
Audio intent: precisão, fechamento
Audio-coupled idea: tick leve por linha, acento na última
Transition mood: soft → Scene 5

### Scene 5 — Punchline — 3.5s
Papel claro. Três linhas riscadas uma a uma: "n8n", "LangChain", "framework de agente". Depois "ukode-core" e a voz serif "o humano decide." Rodapé mono: "Python puro · 29 testes · no ar".
Sequential/interaction: yes — riscos em sequência
Audio intent: aterrissagem calma
Audio-coupled idea: nenhum efeito além da música fechando
Transition mood: fim com fade da música

**Total:** 3.5 + 3.5 + 6.5 + 5 + 3.5 = 22s

**Music mood for this video:** quiet confident
**Audio summary:** bed baixo que sobe discretamente no nome, efeitos pequenos só onde algo acontece na tela, fechamento limpo.
