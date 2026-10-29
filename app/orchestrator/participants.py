"""Registro de participantes del salón (personas y agentes)."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from enum import Enum


class Kind(str, Enum):
    HUMAN = "humano"
    AGENT = "agente"


class Status(str, Enum):
    PENDING = "pendiente"   # agente agregado, esperando aprobación de una persona
    ACTIVE = "activo"
    REJECTED = "rechazado"
    LEFT = "salio"


class Mode(str, Enum):
    NORMAL = "normal"  # lenguaje y velocidad que una persona entiende (por defecto)
    FAST = "rapido"    # comunicación interna; solo con autorización de una persona


@dataclass
class Participant:
    id: str
    name: str
    kind: Kind
    status: Status
    mode: Mode = Mode.NORMAL
    autonomous: bool = False
    autonomous_task: str | None = None
    personality: str = ""

    @property
    def is_human(self) -> bool:
        return self.kind == Kind.HUMAN

    @property
    def is_agent(self) -> bool:
        return self.kind == Kind.AGENT

    @property
    def is_active(self) -> bool:
        return self.status == Status.ACTIVE

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "mode": self.mode.value,
            "autonomous": self.autonomous,
            "autonomous_task": self.autonomous_task,
            "personality": self.personality,
        }


class Registry:
    """Guarda a todos los participantes, activos o no."""

    def __init__(self) -> None:
        self._people: dict[str, Participant] = {}
        self._ids = itertools.count(1)

    def add(self, name: str, kind: Kind, status: Status, personality: str = "") -> Participant:
        prefix = "h" if kind == Kind.HUMAN else "a"
        pid = f"{prefix}{next(self._ids)}"
        p = Participant(id=pid, name=name, kind=kind, status=status, personality=personality)
        self._people[pid] = p
        return p

    def get(self, pid: str) -> Participant:
        try:
            return self._people[pid]
        except KeyError:
            raise KeyError(f"No existe el participante {pid}") from None

    def all(self) -> list[Participant]:
        return list(self._people.values())

    def active(self) -> list[Participant]:
        return [p for p in self._people.values() if p.is_active]

    def active_agents(self) -> list[Participant]:
        return [p for p in self.active() if p.is_agent]

    def active_humans(self) -> list[Participant]:
        return [p for p in self.active() if p.is_human]
