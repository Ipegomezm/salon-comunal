"""El salón: une participantes, turnos, contexto compartido y reglas de modos.

Todas las acciones quedan en la transcripción para que las personas siempre
sepan qué hacen y dicen los agentes (transparencia).
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass
from typing import Callable

from . import context as ctx
from .context import SharedContext
from .participants import Kind, Mode, Participant, Registry, Status
from .turns import FloorError, TurnManager


class RoomError(Exception):
    """Acción no permitida en el salón. El mensaje es para mostrarse a la persona."""


@dataclass
class ModeRequest:
    id: int
    agent_id: str
    reason: str
    status: str = "pendiente"   # pendiente | aprobado | negado
    decided_by: str | None = None

    def to_dict(self) -> dict:
        return {"id": self.id, "agent_id": self.agent_id, "reason": self.reason,
                "status": self.status, "decided_by": self.decided_by}


# Si no hay un organizador (persona) conectado durante este tiempo, el salón se pausa.
# Es también el margen para recargar la página o si se cae la conexión.
DEFAULT_ORGANIZER_GRACE_SECONDS = 60.0
# Frenos de la conversación entre agentes (configurables).
DEFAULT_AGENT_COOLDOWN_SECONDS = 8.0
DEFAULT_AGENT_TURN_BUDGET = 6
# «Baño»: si el organizador se aleja con la página abierta, el salón sigue hasta este límite.
DEFAULT_BATHROOM_LIMIT_SECONDS = 1500.0   # 25 minutos
# Aviso grande arriba en los últimos 5 minutos del «Baño» del organizador
# (decidido por Felipe: se queda, encendido por defecto).
BATHROOM_NOTICE_SECONDS = 300.0


class Room:
    def __init__(
        self,
        name: str = "Salón principal",
        organizer_grace: float = DEFAULT_ORGANIZER_GRACE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        speech_seconds_per_char: float = 0.0,
        agent_cooldown_seconds: float = DEFAULT_AGENT_COOLDOWN_SECONDS,
        agent_turn_budget: int = DEFAULT_AGENT_TURN_BUDGET,
        bathroom_limit: float = DEFAULT_BATHROOM_LIMIT_SECONDS,
        bathroom_notice: bool = True,
    ) -> None:
        self.name = name
        # Freno para que los agentes no conversen sin fin entre ellos:
        # - cada agente espera `agent_cooldown_seconds` después de hablar antes de pedir la palabra;
        # - como máximo `agent_turn_budget` mensajes de agentes seguidos sin que hable una persona.
        self.agent_cooldown_seconds = agent_cooldown_seconds
        self.agent_turn_budget = agent_turn_budget
        self._last_spoke_at: dict[str, float] = {}
        # Reportes de vacíos marcados para que el organizador los vea primero.
        self.flags: list[dict] = []
        self._flag_ids = itertools.count(1)
        # Resumen para el organizador que vuelve.
        self._had_organizer = False
        self._away: dict | None = None
        self.return_summaries: dict[str, dict] = {}
        # Habla simulada (sin audio todavía): un agente conserva la palabra mientras "dice"
        # su texto. 0 = suelta la palabra de inmediato (útil en pruebas).
        self.speech_seconds_per_char = speech_seconds_per_char
        self.speaking: dict | None = None   # {"pid", "entry_id", "started", "until"}
        self.organizer_grace = organizer_grace
        self.clock = clock
        self.paused = False
        self.pause_reason: str | None = None   # "sin_organizador" o "bano"
        self._organizer_absent_since: float | None = clock()  # al arrancar aún no hay organizador
        self._unavailable = True       # sin organizador disponible (se fue o está en «Baño»)
        self.bathroom_limit = bathroom_limit
        self.bathroom_notice = bathroom_notice   # interruptor del aviso grande (SALON_AVISO_BANO)
        self.registry = Registry()
        self.turns = TurnManager()
        self.context = SharedContext()
        self.adapters: dict = {}             # agent_id -> AgentAdapter
        self.mode_requests: dict[int, ModeRequest] = {}
        self._req_ids = itertools.count(1)

    # ---------- ayudas internas ----------
    def _get(self, pid: str) -> Participant:
        try:
            return self.registry.get(pid)
        except KeyError as e:
            raise RoomError(str(e)) from None

    def _active(self, pid: str) -> Participant:
        p = self._get(pid)
        if p.status == Status.PENDING:
            raise RoomError(f"{p.name} todavía espera aprobación.")
        if not p.is_active:
            raise RoomError(f"{p.name} no está en el salón.")
        return p

    def _human(self, pid: str) -> Participant:
        p = self._active(pid)
        if not p.is_human:
            raise RoomError("Solo una persona del salón puede hacer esto.")
        return p

    def _organizer(self, pid: str) -> Participant:
        p = self._active(pid)
        if not p.organizer:
            raise RoomError("Solo el organizador del salón puede hacer esto.")
        if p.away:
            raise RoomError("Estás fuera un rato (Baño). Toca «Ya volví» primero.")
        return p

    def organizers(self) -> list[Participant]:
        return [p for p in self.registry.active() if p.organizer]

    def speech_duration(self, text: str) -> float:
        """Cuánto dura "decir" un texto en la habla simulada (en segundos)."""
        if self.speech_seconds_per_char <= 0:
            return 0.0
        return min(max(len(text) * self.speech_seconds_per_char, 1.2), 9.0)

    def _require_not_paused(self) -> None:
        if self.paused:
            raise RoomError("El salón está en pausa porque no hay un organizador conectado. "
                            "Se reanuda cuando vuelva.")

    # ---------- pausa si no hay organizador ----------
    def human_organizers_present(self) -> bool:
        """¿Hay un organizador (persona) conectado y disponible (no en «Baño»)?"""
        return any(p.is_human and not p.away for p in self.organizers())

    def _connected_human_organizers(self) -> list[Participant]:
        """Organizadores (personas) con la página abierta, estén o no en «Baño»."""
        return [p for p in self.organizers() if p.is_human]

    def _pending_pause(self) -> tuple[str, float] | None:
        """Si el salón va camino a la pausa: (motivo, segundos que faltan). Si no, None."""
        if self.paused or self.human_organizers_present():
            return None
        now = self.clock()
        connected = self._connected_human_organizers()
        if connected:  # todos los organizadores conectados están en «Baño»
            latest = max(p.away_since for p in connected)
            return "bano", max(0.0, self.bathroom_limit - (now - latest))
        if self._organizer_absent_since is None:
            return None
        return "sin_organizador", max(0.0, self.organizer_grace - (now - self._organizer_absent_since))

    def bathroom_notice_info(self) -> dict | None:
        """Aviso grande para todos en los últimos 5 minutos del «Baño» del organizador.

        Devuelve {"name", "seconds_left"} o None (si el aviso está apagado o no aplica).
        """
        if not self.bathroom_notice:
            return None
        pending = self._pending_pause()
        if not pending or pending[0] != "bano" or pending[1] > BATHROOM_NOTICE_SECONDS:
            return None
        who = max(self._connected_human_organizers(), key=lambda p: p.away_since)
        return {"name": who.name, "seconds_left": pending[1]}

    def seconds_until_pause(self) -> float | None:
        """Segundos que faltan para la pausa por falta de organizador conectado
        (None si hay organizador, si está en «Baño» o si ya está pausado)."""
        pending = self._pending_pause()
        if pending and pending[0] == "sin_organizador":
            return pending[1]
        return None

    def check_organizer_presence(self) -> bool:
        """Revisa si hay un organizador (persona) disponible. Devuelve True si algo cambió.

        - Organizador disponible: todo normal. Si volvía de una ausencia, se arma el resumen
          y, si el salón estaba en pausa, se reanuda.
        - Sin organizador disponible (se fue o está en «Baño»): los agentes siguen solos en modo
          normal; lo que necesita decisión queda pendiente.
        - Pausa de TODO el salón:
          * si no hay ningún organizador conectado durante `organizer_grace` (60 s), o
          * si los organizadores conectados llevan más de `bathroom_limit` (25 min) en «Baño».
        """
        now = self.clock()
        changed = False
        if self.human_organizers_present():
            changed = self._organizer_absent_since is not None or self._unavailable
            self._organizer_absent_since = None
            self._unavailable = False
            self._had_organizer = True
            if self._away is not None:
                self._make_return_summary(now)
            if self.paused:
                self.paused = False
                self._log(ctx.SYSTEM, "Volvió un organizador. El salón sigue.")
                return True
            return changed

        if not self._unavailable:  # recién se quedó sin organizador disponible
            self._unavailable = True
            changed = True
            if self._had_organizer and self._away is None:
                last = self.context.entries[-1].id if self.context.entries else 0
                self._away = {"since": now, "since_entry": last, "paused": False}
            self._force_normal_mode()

        if self._connected_human_organizers():
            self._organizer_absent_since = None   # la página sigue abierta: protege «Baño»
        elif self._organizer_absent_since is None:
            self._organizer_absent_since = now
            changed = True

        pending = self._pending_pause()
        if pending and pending[1] <= 0 and not self.paused:
            self.paused = True
            self.pause_reason = pending[0]
            if self._away is not None:
                self._away["paused"] = True
            if pending[0] == "bano":
                mins = int(self.bathroom_limit // 60)
                self._log(ctx.SYSTEM, f"El organizador lleva {mins} minutos fuera (Baño). El salón queda en pausa.")
            else:
                self._log(ctx.SYSTEM, f"No hay un organizador conectado desde hace "
                                      f"{int(self.organizer_grace)} segundos. El salón queda en pausa.")
            return True
        return changed

    # ---------- «Baño»: alejarse un rato ----------
    def step_away(self, pid: str) -> None:
        """Una persona se va un rato. Suelta la palabra y retira su pedido si lo tenía."""
        p = self._human(pid)
        if p.away:
            raise RoomError("Ya estás fuera un rato. Toca «Ya volví» para volver.")
        if self.turns.speaker == pid:
            self.turns.release(pid)
        elif pid in self.turns.queue:
            self.turns.withdraw(pid)
        p.away, p.away_since = True, self.clock()
        self._log(ctx.SYSTEM, f"{p.name} se fue un rato.")
        self._log_speaker_change()

    def come_back(self, pid: str) -> None:
        p = self._human(pid)
        if not p.away:
            raise RoomError("No estabas fuera.")
        p.away, p.away_since = False, None
        self._log(ctx.SYSTEM, f"{p.name} volvió.")

    def _not_away(self, p: Participant) -> None:
        if p.away:
            raise RoomError(f"{p.name} está fuera un rato. Hay que tocar «Ya volví» primero.")

    def _force_normal_mode(self) -> None:
        """Sin organizador conectado, los agentes hablan solo en modo normal."""
        for a in self.registry.active_agents():
            if a.mode == Mode.FAST:
                a.mode = Mode.NORMAL
                self._log(ctx.MODE, f"{a.name} volvió al modo normal porque no hay un organizador conectado.")

    def _make_return_summary(self, now: float) -> None:
        """Arma el resumen de lo que pasó mientras no había organizador."""
        away, self._away = self._away, None
        msgs = [e for e in self.context.entries if e.kind == ctx.MESSAGE and e.id > away["since_entry"]]
        pending_agents = [p.name for p in self.registry.all() if p.is_agent and p.status == Status.PENDING]
        pending_modes = [{"agent": self._get(r.agent_id).name, "reason": r.reason}
                         for r in self.mode_requests.values() if r.status == "pendiente"]
        flags = [f for f in self.flags if not f["reviewed"]]
        if not (msgs or pending_agents or pending_modes or flags or away["paused"]):
            return  # no hay nada que contar (por ejemplo, solo recargó la página)
        secs = int(now - away["since"])
        dur = f"{secs} segundos" if secs < 120 else f"{secs // 60} minutos"
        lines = [f"Estuviste fuera unos {dur}."]
        if msgs:
            counts: dict[str, int] = {}
            for e in msgs:
                counts[e.author_name] = counts.get(e.author_name, 0) + 1
            detail = ", ".join(f"{n} {c}" for n, c in counts.items())
            lines.append(f"Mensajes mientras no estabas: {len(msgs)} ({detail}).")
        else:
            lines.append("Nadie habló mientras no estabas.")
        if away["paused"]:
            lines.append("El salón se pausó porque no había un organizador conectado.")
        lines.append("Agentes que esperan tu aprobación: " + (", ".join(pending_agents) if pending_agents else "ninguno") + ".")
        lines.append("Pedidos de modo rápido por decidir: " + (
            "; ".join(f"{m['agent']} ({m['reason']})" for m in pending_modes) if pending_modes else "ninguno") + ".")
        lines.append(f"Reportes de vacíos sin revisar: {len(flags)}." if flags else "Reportes de vacíos sin revisar: ninguno.")
        summary = {
            "lines": lines,
            "messages": [{"author": e.author_name, "text": e.text, "mode": e.mode} for e in msgs],
            "pending_agents": pending_agents,
            "pending_mode_requests": pending_modes,
            "flags": [dict(f) for f in flags],
            "paused": away["paused"],
            "away_seconds": secs,
        }
        for p in self.organizers():
            if p.is_human:
                self.return_summaries[p.id] = summary

    def pop_return_summary(self, pid: str) -> dict | None:
        return self.return_summaries.pop(pid, None)

    def acknowledge_flag(self, flag_id: int, by: str) -> None:
        """Un organizador marca un reporte de vacío como revisado."""
        org = self._organizer(by)
        for f in self.flags:
            if f["id"] == int(flag_id):
                if f["reviewed"]:
                    raise RoomError("Ese reporte ya fue revisado.")
                f["reviewed"] = True
                self._log(ctx.SYSTEM, f"{org.name} revisó el reporte de vacío de {f['author']}.")
                return
        raise RoomError("Ese reporte no existe.")

    def _agent_messages_since_human(self) -> int:
        n = 0
        for e in reversed(self.context.entries):
            if e.kind != ctx.MESSAGE:
                continue
            if e.author_kind == Kind.HUMAN.value:
                break
            n += 1
        return n

    def agent_budget_left(self) -> int:
        return max(0, self.agent_turn_budget - self._agent_messages_since_human())

    def _last_message_author(self) -> str | None:
        for e in reversed(self.context.entries):
            if e.kind == ctx.MESSAGE:
                return e.author_id
        return None

    def _agent_may_ask(self, agent_id: str) -> bool:
        """Frenos: nunca se responde a sí mismo, espera entre mensajes y tope de turnos."""
        if self.agent_budget_left() <= 0:
            return False
        if self._last_message_author() == agent_id:
            return False
        last = self._last_spoke_at.get(agent_id)
        if last is not None and self.clock() - last < self.agent_cooldown_seconds:
            return False
        return True

    def _agent(self, pid: str) -> Participant:
        p = self._get(pid)
        if not p.is_agent:
            raise RoomError(f"{p.name} no es un agente.")
        return p

    def _log(self, kind: str, text: str, author: Participant | None = None, mode: str = "normal"):
        return self.context.add(kind, text, author, mode)

    # ---------- entrar, salir, aprobar ----------
    def add_human(self, name: str, organizer: bool = False) -> Participant:
        """Una persona entra. `organizer=True` solo lo decide el servidor (link secreto)."""
        name = (name or "").strip() or "Invitado"
        p = self.registry.add(name, Kind.HUMAN, Status.ACTIVE)
        p.organizer = organizer
        extra = " como organizador" if organizer else ""
        self._log(ctx.SYSTEM, f"{p.name} entró al salón{extra}.")
        return p

    # ---------- rol de organizador ----------
    def grant_organizer(self, target: str, by: str) -> Participant:
        """Un organizador (persona) le da el rol a otra persona o a un agente activo.

        Ningún agente puede dar el rol, ni a sí mismo ni a otros.
        """
        granter = self._organizer(by)
        if not granter.is_human:
            raise RoomError("Un agente no puede dar el rol de organizador.")
        t = self._active(target)
        if t.organizer:
            raise RoomError(f"{t.name} ya es organizador.")
        t.organizer = True
        self._log(ctx.SYSTEM, f"{granter.name} le dio el rol de organizador a {t.name}.")
        return t

    def revoke_organizer(self, target: str, by: str) -> Participant:
        """Un organizador (persona) le quita el rol a alguien. Nunca al último organizador."""
        revoker = self._organizer(by)
        if not revoker.is_human:
            raise RoomError("Un agente no puede quitar el rol de organizador.")
        t = self._get(target)
        if not t.organizer:
            raise RoomError(f"{t.name} no es organizador.")
        if t.is_active and len(self.organizers()) <= 1:
            raise RoomError("No se puede quitar el rol al último organizador.")
        t.organizer = False
        self._log(ctx.SYSTEM, f"{revoker.name} le quitó el rol de organizador a {t.name}.")
        return t

    def add_agent(self, adapter, added_by: str | None = None) -> Participant:
        """Agrega un agente. Queda PENDIENTE hasta que una persona lo apruebe."""
        self._require_not_paused()
        who = "El salón"
        if added_by is not None:
            who = self._human(added_by).name
        p = self.registry.add(adapter.name, Kind.AGENT, Status.PENDING, adapter.personality)
        self.adapters[p.id] = adapter
        self._log(ctx.SYSTEM, f"{who} agregó al agente {p.name}. Espera aprobación del organizador.")
        return p

    def approve_agent(self, agent_id: str, by: str) -> Participant:
        human = self._organizer(by)
        agent = self._agent(agent_id)
        if agent.status != Status.PENDING:
            raise RoomError(f"{agent.name} no está esperando aprobación.")
        agent.status = Status.ACTIVE
        self._log(ctx.SYSTEM, f"{human.name} aprobó al agente {agent.name}. Ya está en el salón.")
        return agent

    def reject_agent(self, agent_id: str, by: str) -> Participant:
        human = self._organizer(by)
        agent = self._agent(agent_id)
        if agent.status != Status.PENDING:
            raise RoomError(f"{agent.name} no está esperando aprobación.")
        agent.status = Status.REJECTED
        self._log(ctx.SYSTEM, f"{human.name} no aprobó al agente {agent.name}.")
        return agent

    def leave(self, pid: str) -> None:
        p = self._get(pid)
        if p.status in (Status.LEFT, Status.REJECTED):
            return
        p.status = Status.LEFT
        self.turns.remove(pid)
        self._log(ctx.SYSTEM, f"{p.name} salió del salón.")
        self._log_speaker_change()

    # ---------- contexto compartido ----------
    def context_for(self, pid: str) -> list[dict]:
        """Solo los participantes activos leen el contexto (no los pendientes)."""
        self._active(pid)
        return [e.to_dict() for e in self.context.recent()]

    # ---------- turnos de palabra ----------
    def _log_speaker_change(self) -> None:
        sp = self.turns.speaker
        if sp:
            self._log(ctx.TURN, f"{self._get(sp).name} tiene la palabra.")

    def request_floor(self, pid: str) -> bool:
        self._require_not_paused()
        p = self._active(pid)
        self._not_away(p)
        try:
            granted = self.turns.request(pid)
        except FloorError as e:
            raise RoomError(str(e)) from None
        self._log(ctx.TURN, f"{p.name} pidió la palabra.")
        if granted:
            self._log_speaker_change()
        return granted

    def withdraw_floor(self, pid: str) -> None:
        """Cada quien retira solo su propio pedido."""
        p = self._active(pid)
        try:
            self.turns.withdraw(pid)
        except FloorError as e:
            raise RoomError(str(e)) from None
        self._log(ctx.TURN, f"{p.name} retiró su pedido de palabra.")

    def release_floor(self, pid: str) -> None:
        p = self._get(pid)
        try:
            self.turns.release(pid)
        except FloorError as e:
            raise RoomError(str(e)) from None
        self._log(ctx.TURN, f"{p.name} soltó la palabra.")
        self._log_speaker_change()

    def grant_floor(self, target: str, by: str) -> None:
        """Una persona le da la palabra a alguien (solo si nadie la tiene)."""
        self._require_not_paused()
        human = self._human(by)
        t = self._active(target)
        self._not_away(t)
        try:
            self.turns.grant(target)
        except FloorError as e:
            raise RoomError(str(e)) from None
        self._log(ctx.TURN, f"{human.name} le dio la palabra a {t.name}.")
        self._log_speaker_change()

    def interrupt(self, pid: str) -> None:
        """Solo una persona puede interrumpir, y solo a un agente."""
        self._require_not_paused()
        human = self._human(pid)
        self._not_away(human)
        sp = self.turns.speaker
        if sp is None:
            raise RoomError("Nadie tiene la palabra; no hace falta interrumpir.")
        current = self._get(sp)
        if current.is_human:
            raise RoomError(f"{current.name} tiene la palabra. Pide la palabra y espera tu turno.")
        try:
            self.turns.interrupt(pid)
        except FloorError as e:
            raise RoomError(str(e)) from None
        self._log(ctx.TURN, f"{human.name} interrumpió a {current.name}.")
        self._log_speaker_change()

    def say(self, pid: str, text: str, mode: Mode | str = Mode.NORMAL) -> None:
        """Hablar. Requiere tener la palabra. El modo rápido requiere autorización."""
        self._require_not_paused()
        p = self._active(pid)
        self._not_away(p)
        text = (text or "").strip()
        if not text:
            raise RoomError("El mensaje está vacío.")
        if self.turns.speaker != pid:
            raise RoomError("Para hablar necesitas tener la palabra.")
        mode = Mode(mode)
        if mode == Mode.FAST and p.mode != Mode.FAST:
            self._log(ctx.MODE, f"Se bloqueó un mensaje de {p.name} en modo rápido: no tiene autorización.")
            raise RoomError(f"{p.name} no tiene autorización para el modo rápido.")
        self._log(ctx.MESSAGE, text, p, mode.value)
        if p.is_agent:
            self._last_spoke_at[pid] = self.clock()

    def speak_now(self, pid: str, text: str) -> None:
        """Atajo para personas en el chat de texto: toma la palabra, habla y la suelta.

        - Si la persona ya tiene la palabra, solo habla (y la conserva).
        - Si nadie la tiene, la toma, habla y la suelta.
        - Si la tiene un agente, la persona lo interrumpe.
        - Si la tiene otra persona, debe esperar su turno.
        """
        self._require_not_paused()
        self._not_away(self._human(pid))
        if not (text or "").strip():
            raise RoomError("El mensaje está vacío.")
        sp = self.turns.speaker
        if sp == pid:
            self.say(pid, text)
            return
        if sp is None:
            self.turns.grant(pid)
        else:
            self.interrupt(pid)
        self.say(pid, text)
        self.turns.release(pid)
        self._log_speaker_change()

    # ---------- modos de comunicación ----------
    def request_fast_mode(self, agent_id: str, reason: str) -> ModeRequest:
        self._require_not_paused()
        agent = self._active(agent_id)
        if not agent.is_agent:
            raise RoomError("Solo los agentes piden el modo rápido.")
        if agent.mode == Mode.FAST:
            raise RoomError(f"{agent.name} ya está en modo rápido.")
        for r in self.mode_requests.values():
            if r.agent_id == agent_id and r.status == "pendiente":
                return r
        req = ModeRequest(id=next(self._req_ids), agent_id=agent_id, reason=reason or "(sin motivo)")
        self.mode_requests[req.id] = req
        self._log(ctx.MODE, f"{agent.name} pide pasar a modo rápido. Motivo: {req.reason}. "
                            f"Sigue en modo normal hasta que el organizador lo autorice.")
        return req

    def decide_mode_request(self, request_id: int, by: str, approve: bool) -> ModeRequest:
        """Solo un organizador que sea PERSONA decide el modo rápido.

        Un agente con rol de organizador nunca puede autorizar ni negar el modo
        rápido, ni para sí mismo ni para otros agentes.
        """
        human = self._organizer(by)
        if not human.is_human:
            raise RoomError("Un agente no puede decidir el modo rápido, aunque sea organizador. "
                            "Solo una persona organizadora puede hacerlo.")
        req = self.mode_requests.get(int(request_id))
        if req is None:
            raise RoomError("Ese pedido no existe.")
        if req.status != "pendiente":
            raise RoomError("Ese pedido ya fue decidido.")
        agent = self._get(req.agent_id)
        req.decided_by = human.id
        if approve and agent.is_active:
            req.status = "aprobado"
            agent.mode = Mode.FAST
            self._log(ctx.MODE, f"{human.name} autorizó a {agent.name} a usar el modo rápido.")
        else:
            req.status = "negado"
            self._log(ctx.MODE, f"{human.name} negó el modo rápido a {agent.name}. Sigue en modo normal.")
        return req

    def back_to_normal(self, agent_id: str, by: str) -> None:
        """Una persona (o el mismo agente) devuelve al agente al modo normal."""
        actor = self._active(by)
        agent = self._agent(agent_id)
        if actor.is_agent and actor.id != agent_id:
            raise RoomError("Un agente no puede cambiar el modo de otro.")
        if agent.mode == Mode.NORMAL:
            return
        agent.mode = Mode.NORMAL
        self._log(ctx.MODE, f"{agent.name} volvió al modo normal (lo decidió {actor.name}).")

    def report_loophole(self, pid: str, description: str) -> None:
        p = self._active(pid)
        e = self._log(ctx.LOOPHOLE, f"{p.name} reporta un vacío en la regla: {description}", p)
        # Queda marcado para que el organizador lo vea primero.
        self.flags.append({"id": next(self._flag_ids), "entry_id": e.id, "author": p.name,
                           "text": description, "reviewed": False})

    # ---------- trabajo autónomo ----------
    def start_autonomous(self, agent_id: str, task: str, by: str) -> None:
        self._require_not_paused()
        human = self._human(by)
        agent = self._active(agent_id)
        if not agent.is_agent:
            raise RoomError("Solo los agentes trabajan de forma autónoma aquí.")
        task = (task or "").strip() or "tarea sin nombre"
        agent.autonomous, agent.autonomous_task = True, task
        if agent_id in self.turns.queue:
            self.turns.withdraw(agent_id)
        self.adapters[agent_id].on_autonomous_start(task)
        self._log(ctx.AUTONOMOUS, f"{human.name} mandó a {agent.name} a trabajar por su cuenta en: {task}. "
                                  f"No reportará cada paso.")

    def end_autonomous(self, agent_id: str, by: str) -> None:
        self._require_not_paused()
        actor = self._active(by)
        agent = self._agent(agent_id)
        if actor.is_agent and actor.id != agent_id:
            raise RoomError("Un agente no puede terminar el trabajo de otro.")
        if not agent.autonomous:
            raise RoomError(f"{agent.name} no está trabajando solo.")
        agent.autonomous, task = False, agent.autonomous_task
        agent.autonomous_task = None
        self.adapters[agent_id].on_autonomous_end()
        self._log(ctx.AUTONOMOUS, f"{agent.name} terminó su trabajo autónomo ({task}).")

    # ---------- agentes ----------
    def view_for(self, agent_id: str):
        from app.agents.base import AgentView
        p = self._active(agent_id)
        return AgentView(
            me_id=p.id, me_name=p.name, my_mode=p.mode.value, autonomous=p.autonomous,
            transcript=self.context_for(agent_id),
            participants=[x.to_dict() for x in self.registry.active()],
            speaker=self.turns.speaker, queue=list(self.turns.queue),
        )

    def agent_tick(self) -> bool:
        """Un paso de los agentes. Devuelve True si algo cambió.

        1) Los agentes en fila pueden retirar su pedido si ya no es relevante.
        2) Si un agente tiene la palabra: dice lo suyo y la suelta (si la habla simulada
           está activa, la suelta cuando termina de "hablar").
        3) Si no: cada agente activo decide si pide la palabra.
        """
        if self.paused:
            return False
        changed = False
        # 1) Los agentes en fila revisan si su pedido sigue siendo relevante.
        # Si ya se gastaron los turnos de agentes, retiran su pedido hasta que hable una persona.
        budget_spent = self.agent_budget_left() <= 0
        for agent_id in list(self.turns.queue):
            if not self._get(agent_id).is_agent:
                continue
            if budget_spent or not self.adapters[agent_id].still_relevant(self.view_for(agent_id)):
                self.withdraw_floor(agent_id)
                changed = True

        # 2) Si un agente tiene la palabra: habla y la suelta.
        sp = self.turns.speaker
        if self.speaking and self.speaking["pid"] != sp:
            self.speaking = None   # lo interrumpieron o salió
        if sp and self.speaking:
            if self.clock() < self.speaking["until"]:
                return changed     # sigue "hablando": conserva la palabra
            self.speaking = None
            self.release_floor(sp)
            return True
        if sp and self._get(sp).is_agent:
            agent = self._get(sp)
            adapter = self.adapters[sp]
            if budget_spent or not adapter.still_relevant(self.view_for(sp)):
                self.turns.release(sp)
                self._log(ctx.TURN, f"{agent.name} cedió la palabra sin hablar: ya no era relevante.")
                self._log_speaker_change()
                return True
            reply = adapter.respond(self.view_for(sp))
            if reply.report_loophole:
                self.report_loophole(sp, reply.report_loophole)
            if reply.request_fast_mode and agent.mode != Mode.FAST:
                self.request_fast_mode(sp, reply.request_fast_mode)
            if reply.text:
                try:
                    self.say(sp, reply.text, reply.mode)
                    duration = self.speech_duration(reply.text)
                    if duration > 0:
                        now = self.clock()
                        self.speaking = {"pid": sp, "entry_id": self.context.entries[-1].id,
                                         "started": now, "until": now + duration}
                        return True   # suelta la palabra cuando termine de "hablar"
                except RoomError:
                    pass  # ya quedó registrado en la transcripción
            if self.turns.speaker == sp:
                self.release_floor(sp)
            return True

        # 3) Los demás agentes deciden si piden la palabra.
        for agent in self.registry.active_agents():
            if agent.id in self.turns.queue or agent.id == self.turns.speaker:
                continue
            if not self._agent_may_ask(agent.id):
                continue
            if self.adapters[agent.id].wants_floor(self.view_for(agent.id)):
                self.request_floor(agent.id)
                changed = True
        return changed

    # ---------- estado para la página ----------
    def _participant_view(self, p: Participant) -> dict:
        d = p.to_dict()
        d["away_seconds"] = (self.clock() - p.away_since) if p.away and p.away_since is not None else None
        return d

    def snapshot(self, viewer: str | None = None) -> dict:
        """Estado para la página. Los pedidos de modo rápido por decidir solo se
        mandan a organizadores que son personas (igual quedan en la transcripción)."""
        is_org = can_decide_fast = False
        if viewer:
            try:
                v = self.registry.get(viewer)
                is_org = v.is_active and v.organizer
                can_decide_fast = is_org and v.is_human
            except KeyError:
                pass
        return {
            "you_are_organizer": is_org,
            "paused": self.paused,
            "pause_reason": self.pause_reason if self.paused else None,
            "seconds_until_pause": self.seconds_until_pause(),
            "speech_seconds_per_char": self.speech_seconds_per_char,
            "flags": [f for f in self.flags if not f["reviewed"]] if is_org else [],
            "agent_budget_left": self.agent_budget_left(),
            "you_can_decide_fast_mode": can_decide_fast,
            "room": self.name,
            "participants": [self._participant_view(p) for p in self.registry.all()
                             if p.status in (Status.ACTIVE, Status.PENDING)],
            "bathroom_limit": self.bathroom_limit,
            "bathroom_notice": self.bathroom_notice_info(),
            "speaker": self.turns.speaker,
            "queue": list(self.turns.queue),
            "mode_requests": [r.to_dict() for r in self.mode_requests.values()] if can_decide_fast else [],
            "transcript": [e.to_dict() for e in self.context.recent(300)],
        }
