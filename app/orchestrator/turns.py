"""Motor de turnos de palabra.

Reglas:
- Nunca hay dos personas o agentes con la palabra al mismo tiempo.
- Quien pide la palabra entra a una fila. Si nadie tiene la palabra, la recibe
  el primero de la fila.
- Cada quien puede retirar SOLO su propio pedido.
- Quien tiene la palabra la suelta y pasa al siguiente de la fila.
- Las interrupciones quitan la palabra al que habla y se la dan a otro.
  (Quién puede interrumpir lo decide el salón, no este motor.)
"""
from __future__ import annotations


class FloorError(Exception):
    """Acción de turnos no permitida."""


class TurnManager:
    def __init__(self) -> None:
        self.speaker: str | None = None
        self.queue: list[str] = []

    def request(self, pid: str) -> bool:
        """Pide la palabra. Devuelve True si la recibió de inmediato."""
        if pid == self.speaker:
            raise FloorError("Ya tienes la palabra.")
        if pid not in self.queue:
            self.queue.append(pid)
        self._advance()
        return self.speaker == pid

    def withdraw(self, pid: str) -> None:
        """Retira el propio pedido de palabra."""
        if pid not in self.queue:
            raise FloorError("No habías pedido la palabra.")
        self.queue.remove(pid)

    def release(self, pid: str) -> str | None:
        """Suelta la palabra. Devuelve quién la recibe ahora (o None)."""
        if self.speaker != pid:
            raise FloorError("No tienes la palabra.")
        self.speaker = None
        self._advance()
        return self.speaker

    def grant(self, pid: str) -> None:
        """Da la palabra directamente a alguien, solo si nadie la tiene."""
        if self.speaker is not None:
            raise FloorError("Alguien ya tiene la palabra.")
        if pid in self.queue:
            self.queue.remove(pid)
        self.speaker = pid

    def interrupt(self, pid: str) -> str | None:
        """pid toma la palabra quitándosela a quien hablaba. Devuelve al interrumpido."""
        previous = self.speaker
        if previous == pid:
            raise FloorError("Ya tienes la palabra.")
        if pid in self.queue:
            self.queue.remove(pid)
        self.speaker = pid
        return previous

    def remove(self, pid: str) -> None:
        """Saca a alguien de los turnos (por ejemplo, si sale del salón)."""
        if pid in self.queue:
            self.queue.remove(pid)
        if self.speaker == pid:
            self.speaker = None
            self._advance()

    def _advance(self) -> None:
        if self.speaker is None and self.queue:
            self.speaker = self.queue.pop(0)
