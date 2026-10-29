"""Núcleo del orquestador: participantes, turnos, contexto compartido y reglas."""
from .participants import Kind, Mode, Participant, Registry, Status
from .turns import FloorError, TurnManager
from .context import Entry, SharedContext
from .room import ModeRequest, Room, RoomError

__all__ = [
    "Kind", "Mode", "Participant", "Registry", "Status",
    "FloorError", "TurnManager", "Entry", "SharedContext",
    "ModeRequest", "Room", "RoomError",
]
