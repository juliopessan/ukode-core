# Hyperframes Composition Brief: ukode-core

## Objective
Vídeo curto de lançamento do ukode-core: o agente que para e pede permissão.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080, 30fps
- Duration: 23s

## Source Material
- Project root: `ukode-core/`
- Primary files read: `site/live.html` (UI ao vivo), `site/assets/camadas.css` e `site/index.html` (tokens Ledger), `README.md`, `src/ukode_core/orchestrator/engine.py`, `src/ukode_core/policy/policies/demo_agent.yaml`, e o replay de um run real (`beca3f65`).
- Product name: ukode-core (UKode Labs)
- Strongest claim: política avaliada fora do agente, aprovação humana e auditoria de 8 perguntas, em Python puro, sem framework de agente.
- Key UI to recreate: o console escuro de `live.html` com as linhas de política, a caixa "Aprovação pendente" com o botão "Aprovar", e o painel "replay · 8 perguntas".
- Copy verbatim (do produto e do run real):
  - `política  lookup_contact — permitido`
  - `política  send_whatsapp_message — precisa de aprovação`
  - "Envio de WhatsApp para um cliente real exige aprovação humana."
  - "replay · 8 perguntas", "Auditoria íntegra?" / "sim, verificada"
  - `claude-sonnet-5`, `$0.013743`, `lookup_contact, send_whatsapp_message`

## Creative Direction
- Tone preset: polished
- Creative direction: o livro-razão como protagonista
- Interpretation: holds longos, movimento contido, tipografia grande; o único efeito "barulhento" é o carimbo.
- Angle: todo mundo mostra o agente agindo; nós mostramos o agente parando para pedir permissão, um humano decidindo, e o recibo completo.
- Hook: chamada `send_whatsapp_message(...)` digitada num console escuro; carimbo clay "PRECISA DE APROVAÇÃO".
- Outro: "n8n", "LangChain", "framework de agente" riscados → "ukode-core" + voz serif "o humano decide."
- Avoid: linguagem SaaS genérica, filler abstrato, redesenho fora do Ledger, sombras, gradientes, neon.

## Visual Identity (Ledger — regras não negociáveis)
- Background: `#f2efe8` (paper) em todas as cenas; superfície `#e7e3da`; regras `#d6d2c8`
- Ledger inset: `#14140f`, texto `#efece4`, dim `#85817a`, regra `#2c2b25`
- Text: `#11110f`, soft `#55524b`, faint `#8a867c`
- Clay `#ed6738` / `#c8481c` = SOMENTE pendente/não verificado. Mint `#4f9c6b` / `#8fcfa6` = SOMENTE verificado/permitido. Nenhum outro uso.
- Display: Archivo 800 · Instrumento: IBM Plex Mono 400/500 · Voz: Instrument Serif itálico, uma vez no vídeo.
- Sem sombras, sem elevação; regras finas e contraste de fundo separam as áreas.

## Privacidade
Sem hostnames, e-mails ou chaves. Aprovador = "ops". Telefone mascarado.

## Storyboard (contrato: `brag-plan.md`)
1. Hook — 0–3.5s — "Seu agente quer agir." + chamada digitada + carimbo.
2. Reveal — 3.5–7.0s — "ukode-core" + quatro termos um a um.
3. Fluxo ao vivo — 7.0–14.2s — linhas do console, caixa de aprovação, clique em Aprovar, status concluído.
4. Replay — 14.2–19.2s — oito perguntas preenchendo, termina em "sim, verificada".
5. Punchline — 19.2–23.0s — três riscos, nome, voz serif, rodapé factual.

## Audio
- Audio role: sparse professional accents over a warm low bed
- Music: `happy-beats-business-moves-vol-11-by-ende-dot-app.mp3`, baixa, fade-in curto, fade-out nos últimos 1.5s
- Music cue guidance: preset `assets/music/cues/…vol-11….music-cues.json`. Strong cues travados: 1.60s (carimbo), 12.65s (clique em Aprovar), 17.91s ("sim, verificada"). Beat grid para linhas do console e do replay.
- Audio-reactive treatment: none — tom polished e o sistema Ledger proíbe brilho/elevação decorativos; documentado como escolha.
- Audio-coupled moments: teclas na digitação; impacto macio no carimbo; ticks baixos por linha; clique no Aprovar; acento discreto na linha verificada.
- SFX: low HF risk (`sfx-analysis.md`), sempre abaixo da música.
