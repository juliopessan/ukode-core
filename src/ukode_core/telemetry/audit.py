"""Trilha de auditoria só de inserção, encadeada por hash: cada entrada inclui
o hash da anterior, então editar um registro antigo quebra a cadeia visível
de qualquer entrada posterior em diante. Item 05 da camada UKode."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from ukode_core.models import AuditLogEntry


def _hash(prev_hash: str, run_id: str, seq: int, event_type: str, payload: dict) -> str:
    body = json.dumps(
        {"prev_hash": prev_hash, "run_id": run_id, "seq": seq, "event_type": event_type, "payload": payload},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, session: Session):
        self._session = session

    def append(self, run_id: str, event_type: str, payload: dict) -> AuditLogEntry:
        last = (
            self._session.query(AuditLogEntry)
            .filter(AuditLogEntry.run_id == run_id)
            .order_by(AuditLogEntry.seq.desc())
            .first()
        )
        seq = (last.seq + 1) if last else 0
        prev_hash = last.hash if last else ""
        entry_hash = _hash(prev_hash, run_id, seq, event_type, payload)

        entry = AuditLogEntry(
            run_id=run_id,
            seq=seq,
            event_type=event_type,
            payload=payload,
            prev_hash=prev_hash,
            hash=entry_hash,
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    def verify_chain(self, run_id: str) -> bool:
        """Recalcula a cadeia inteira e confere que nada foi alterado."""
        entries = (
            self._session.query(AuditLogEntry)
            .filter(AuditLogEntry.run_id == run_id)
            .order_by(AuditLogEntry.seq)
            .all()
        )
        prev_hash = ""
        for entry in entries:
            expected = _hash(prev_hash, run_id, entry.seq, entry.event_type, entry.payload)
            if expected != entry.hash or entry.prev_hash != prev_hash:
                return False
            prev_hash = entry.hash
        return True
