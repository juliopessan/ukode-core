"""Worker standalone: processa runs pendentes direto do Postgres, sem fila
externa (Redis/Celery/RabbitMQ). Usa `SELECT ... FOR UPDATE SKIP LOCKED`, que
o Postgres já resolve nativamente — dois workers concorrentes nunca pegam o
mesmo run. Rode quantas réplicas quiser; escalar é subir mais processos.

Isto processa apenas runs que ficaram `pending` sem serem iniciados pela API
(ex.: se a criação for assíncrona) — a demo síncrona da API já avança o run
sozinha. Em produção, prefira sempre criar o run como `pending` e deixar o
worker avançar, para a API responder rápido e não segurar a conexão HTTP
enquanto o modelo pensa."""

from __future__ import annotations

import asyncio
import logging
import signal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ukode_core.api.deps import build_engine
from ukode_core.db import SessionLocal, init_db
from ukode_core.models import Run, RunStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ukode_core.worker")

POLL_INTERVAL_SECONDS = 2.0


def _claim_next_run(session: Session) -> Run | None:
    is_postgres = session.bind.dialect.name == "postgresql"
    stmt = select(Run).where(Run.status == RunStatus.PENDING).order_by(Run.created_at).limit(1)
    if is_postgres:
        stmt = stmt.with_for_update(skip_locked=True)
    run = session.execute(stmt).scalar_one_or_none()
    if run is not None:
        run.status = RunStatus.RUNNING
        session.flush()
    return run


async def _process_once() -> bool:
    """Processa um run pendente, se houver. Retorna True se processou algo."""
    session = SessionLocal()
    try:
        run = _claim_next_run(session)
        if run is None:
            session.commit()
            return False

        engine = build_engine(session)
        # o Run já está persistido como RUNNING; a mensagem inicial já está
        # em run.messages, então avançamos direto pelo motor de política.
        await engine._advance(run, engine._agents[run.agent_id])  # noqa: SLF001
        session.commit()
        logger.info("run %s processado (status=%s)", run.id, run.status)
        return True
    except Exception:
        session.rollback()
        logger.exception("falha ao processar run")
        return True
    finally:
        session.close()


async def run_forever() -> None:
    init_db()
    stop = asyncio.Event()

    def _handle_signal(*_args) -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_event_loop().add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass  # Windows

    logger.info("worker iniciado, aguardando runs pendentes...")
    while not stop.is_set():
        processed = await _process_once()
        if not processed:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_forever())
