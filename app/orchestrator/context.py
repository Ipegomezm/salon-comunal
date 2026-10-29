"""Contexto compartido: la transcripción que todos los participantes activos leen."""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field


# Tipos de entrada en la transcripción
MESSAGE = "mensaje"       # alguien habló
SYSTEM = "sistema"        # entradas, salidas, aprobaciones
TURN = "turno"            # cambios de palabra
MODE = "modo"             # pedidos y decisiones de modo rápido
LOOPHOLE = "vacio"        # reporte de un vacío en la regla
AUTONOMOUS = "autonomo"   # inicio/fin de trabajo autónomo


@dataclass
class Entry:
    id: int
    kind: str
    text: str
    author_id: str | None = None
    author_name: str | None = None
    author_kind: str | None = None
    mode: str = "normal"
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "text": self.text,
            "author_id": self.author_id, "author_name": self.author_name,
            "author_kind": self.author_kind, "mode": self.mode, "ts": self.ts,
        }


class SharedContext:
    def __init__(self) -> None:
        self.entries: list[Entry] = []
        self._ids = itertools.count(1)

    def add(self, kind: str, text: str, author=None, mode: str = "normal") -> Entry:
        e = Entry(
            id=next(self._ids), kind=kind, text=text,
            author_id=author.id if author else None,
            author_name=author.name if author else None,
            author_kind=author.kind.value if author else None,
            mode=mode,
        )
        self.entries.append(e)
        return e

    def recent(self, n: int | None = None) -> list[Entry]:
        return list(self.entries if n is None else self.entries[-n:])
