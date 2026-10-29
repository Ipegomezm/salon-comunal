"""Interfaz común que todo agente implementa.

La idea: el orquestador solo habla con esta interfaz. Más adelante, cada agente
puede usar un proveedor de voz distinto (un `VoiceBackend` propio) sin que el
orquestador cambie.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentView:
    """Lo que un agente activo puede ver del salón en un momento dado."""
    me_id: str
    me_name: str
    my_mode: str                     # "normal" o "rapido"
    autonomous: bool
    transcript: list[dict]           # contexto compartido (Entry.to_dict())
    participants: list[dict]         # participantes activos
    speaker: str | None
    queue: list[str] = field(default_factory=list)


@dataclass
class AgentReply:
    """Lo que el agente hace cuando tiene la palabra."""
    text: str | None = None
    mode: str = "normal"             # modo en que quiere decirlo (el salón lo valida)
    request_fast_mode: str | None = None   # motivo, si pide pasar a modo rápido
    report_loophole: str | None = None     # descripción, si reporta un vacío en la regla


class VoiceBackend(ABC):
    """Proveedor de voz de un agente (etapa 3). Cada agente puede tener uno distinto."""

    @abstractmethod
    async def speech_to_text(self, audio: bytes) -> str: ...

    @abstractmethod
    async def text_to_speech(self, text: str) -> bytes: ...


class TextOnlyVoice(VoiceBackend):
    """Etapa 1: sin voz. No usa ninguna API ni clave."""

    async def speech_to_text(self, audio: bytes) -> str:
        raise NotImplementedError("La voz llega en la etapa 3.")

    async def text_to_speech(self, text: str) -> bytes:
        raise NotImplementedError("La voz llega en la etapa 3.")


class AgentAdapter(ABC):
    """Contrato entre el orquestador y un agente."""

    name: str = "Agente"
    personality: str = ""
    voice: VoiceBackend = TextOnlyVoice()

    @abstractmethod
    def wants_floor(self, view: AgentView) -> bool:
        """¿Quiere pedir la palabra ahora?"""

    def still_relevant(self, view: AgentView) -> bool:
        """Si ya pidió la palabra: ¿sigue siendo relevante? Si no, retira su pedido."""
        return True

    @abstractmethod
    def respond(self, view: AgentView) -> AgentReply:
        """Tiene la palabra: decide qué decir."""

    def on_autonomous_start(self, task: str) -> None:
        """Una persona lo mandó a trabajar por su cuenta."""

    def on_autonomous_end(self) -> None:
        """Terminó el trabajo autónomo (puede pedir la palabra para contar el resultado)."""
