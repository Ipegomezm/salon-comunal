"""El salón: une participantes, turnos, contexto compartido y reglas de modos.

Todas las acciones quedan en la transcripción para que las personas siempre
sepan qué hacen y dicen los agentes (transparencia).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

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


class Room:
    def __init__(self, name: str = "Salón principal") -> None:
        self.name = name
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
        return p

    def organizers(self) -> list[Participant]:
        return [p for p in self.registry.active() if p.organizer]

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
        p = self._active(pid)
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
        human = self._human(by)
        t = self._active(target)
        try:
            self.turns.grant(target)
        except FloorError as e:
            raise RoomError(str(e)) from None
        self._log(ctx.TURN, f"{human.name} le dio la palabra a {t.name}.")
        self._log_speaker_change()

    def interrupt(self, pid: str) -> None:
        """Solo una persona puede interrumpir, y solo a un agente."""
        human = self._human(pid)
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
        p = self._active(pid)
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

    def speak_now(self, pid: str, text: str) -> None:
        """Atajo para personas en el chat de texto: toma la palabra, habla y la suelta.

        - Si la persona ya tiene la palabra, solo habla (y la conserva).
        - Si nadie la tiene, la toma, habla y la suelta.
        - Si la tiene un agente, la persona lo interrumpe.
        - Si la tiene otra persona, debe esperar su turno.
        """
        self._human(pid)
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
        self._log(ctx.LOOPHOLE, f"{p.name} reporta un vacío en la regla: {description}", p)

    # ---------- trabajo autónomo ----------
    def start_autonomous(self, agent_id: str, task: str, by: str) -> None:
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
        2) Si un agente tiene la palabra: dice lo suyo y la suelta.
        3) Si no: cada agente activo decide si pide la palabra.
        """
        changed = False
        # 1) Los agentes en fila revisan si su pedido sigue siendo relevante.
        for agent_id in list(self.turns.queue):
            if self._get(agent_id).is_agent and not self.adapters[agent_id].still_relevant(self.view_for(agent_id)):
                self.withdraw_floor(agent_id)
                changed = True

        # 2) Si un agente tiene la palabra: habla y la suelta.
        sp = self.turns.speaker
        if sp and self._get(sp).is_agent:
            agent = self._get(sp)
            adapter = self.adapters[sp]
            if not adapter.still_relevant(self.view_for(sp)):
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
                except RoomError:
                    pass  # ya quedó registrado en la transcripción
            if self.turns.speaker == sp:
                self.release_floor(sp)
            return True

        # 3) Los demás agentes deciden si piden la palabra.
        for agent in self.registry.active_agents():
            if agent.id in self.turns.queue or agent.id == self.turns.speaker:
                continue
            if self.adapters[agent.id].wants_floor(self.view_for(agent.id)):
                self.request_floor(agent.id)
                changed = True
        return changed

    # ---------- estado para la página ----------
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
            "you_can_decide_fast_mode": can_decide_fast,
            "room": self.name,
            "participants": [p.to_dict() for p in self.registry.all()
                             if p.status in (Status.ACTIVE, Status.PENDING)],
            "speaker": self.turns.speaker,
            "queue": list(self.turns.queue),
            "mode_requests": [r.to_dict() for r in self.mode_requests.values()] if can_decide_fast else [],
            "transcript": [e.to_dict() for e in self.context.recent(300)],
        }
