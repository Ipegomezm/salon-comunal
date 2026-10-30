"""Servidor web: página + WebSocket. Corre con:  uvicorn app.server:app --reload"""
from __future__ import annotations

import asyncio
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents.mock import make_mock
from app.orchestrator import Room, RoomError

STATIC = Path(__file__).parent / "static"
TICK_SECONDS = float(os.environ.get("SALON_TICK", "1.5"))  # pausa entre pasos de los agentes
# Segundos sin organizador conectado antes de pausar el salón (también es el margen para recargar).
ORGANIZER_GRACE_SECONDS = float(os.environ.get("SALON_ORGANIZER_GRACE", "60"))
# Habla simulada: segundos por letra que un agente conserva la palabra mientras "habla".
SPEECH_SECONDS_PER_CHAR = float(os.environ.get("SALON_SPEECH_RATE", "0.055"))
# Frenos de la conversación entre agentes.
AGENT_COOLDOWN_SECONDS = float(os.environ.get("SALON_AGENT_COOLDOWN", "8"))
AGENT_TURN_BUDGET = int(os.environ.get("SALON_AGENT_BUDGET", "6"))
# «Baño»: segundos que el organizador puede estar fuera (con la página abierta) antes de pausar el salón.
BATHROOM_LIMIT_SECONDS = float(os.environ.get("SALON_LIMITE_BANO", "1500"))
# Voz (prototipo): dictar con la voz, SOLO en la computadora de cada persona (nunca en la nube).
# Apagada por defecto. Para encenderla: SALON_VOZ=1
VOICE_ENABLED = os.environ.get("SALON_VOZ", "0").strip().lower() in ("1", "si", "sí", "true", "on")

# Aviso grande en los últimos 5 minutos del «Baño» del organizador. Encendido por defecto
# (decidido por Felipe: se queda). Para apagarlo: SALON_AVISO_BANO=0
BATHROOM_NOTICE = os.environ.get("SALON_AVISO_BANO", "1").strip().lower() not in ("0", "no", "false", "off")
PORT_HINT = os.environ.get("SALON_URL", "http://localhost:8000")


def organizer_token() -> str:
    """Clave secreta del organizador.

    Si existe la variable SALON_ORGANIZER_TOKEN se usa esa (queda fija).
    Si no, se inventa una nueva cada vez que el servidor arranca.
    """
    return os.environ.get("SALON_ORGANIZER_TOKEN") or secrets.token_urlsafe(16)


def build_default_room() -> Room:
    """Salón de prueba con tres agentes que esperan aprobación."""
    room = Room(organizer_grace=ORGANIZER_GRACE_SECONDS, speech_seconds_per_char=SPEECH_SECONDS_PER_CHAR,
                agent_cooldown_seconds=AGENT_COOLDOWN_SECONDS, agent_turn_budget=AGENT_TURN_BUDGET,
                bathroom_limit=BATHROOM_LIMIT_SECONDS, bathroom_notice=BATHROOM_NOTICE)
    for style in ("creativa", "critica", "practica"):
        room.add_agent(make_mock(style))
    return room


class Hub:
    """Conexiones abiertas de las personas y envío del estado a todos."""

    def __init__(self, room: Room) -> None:
        self.room = room
        self.sockets: dict[WebSocket, str] = {}

    async def broadcast(self) -> None:
        for ws, pid in list(self.sockets.items()):
            try:
                await ws.send_json({"type": "state", "you": pid, "state": self.room.snapshot(viewer=pid)})
            except Exception:
                self.sockets.pop(ws, None)


def handle_action(room: Room, pid: str, msg: dict) -> None:
    a = msg.get("action")
    if a == "say":
        room.speak_now(pid, msg.get("text", ""))
    elif a == "request_floor":
        room.request_floor(pid)
    elif a == "withdraw_floor":
        room.withdraw_floor(pid)
    elif a == "release_floor":
        room.release_floor(pid)
    elif a == "interrupt":
        room.interrupt(pid)
    elif a == "approve_agent":
        room.approve_agent(msg["agent_id"], by=pid)
    elif a == "reject_agent":
        room.reject_agent(msg["agent_id"], by=pid)
    elif a == "decide_mode":
        room.decide_mode_request(int(msg["request_id"]), by=pid, approve=bool(msg.get("approve")))
    elif a == "back_to_normal":
        room.back_to_normal(msg["agent_id"], by=pid)
    elif a == "start_autonomous":
        room.start_autonomous(msg["agent_id"], msg.get("task", ""), by=pid)
    elif a == "end_autonomous":
        room.end_autonomous(msg["agent_id"], by=pid)
    elif a == "step_away":
        room.step_away(pid)
    elif a == "come_back":
        room.come_back(pid)
    elif a == "ack_flag":
        room.acknowledge_flag(int(msg["flag_id"]), by=pid)
    elif a == "add_agent":
        style = msg.get("style", "creativa")
        if style not in ("creativa", "critica", "practica"):
            raise RoomError("Tipo de agente desconocido.")
        room.add_agent(make_mock(style, (msg.get("name") or "").strip() or None), added_by=pid)
    else:
        raise RoomError("Acción desconocida.")


def create_app(room: Room | None = None, run_agents: bool = True, token: str | None = None) -> FastAPI:
    hub = Hub(room or build_default_room())
    token = token or organizer_token()

    async def agent_loop() -> None:
        while True:
            await asyncio.sleep(TICK_SECONDS)
            try:
                changed = hub.room.check_organizer_presence()
                countdown = hub.room.seconds_until_pause() is not None or hub.room.bathroom_notice_info() is not None
                if hub.room.agent_tick() or changed or countdown:
                    await hub.broadcast()  # (también actualiza la cuenta regresiva)
            except Exception as e:  # no tumbar el servidor por un agente
                print("Error en agentes:", e)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(agent_loop()) if run_agents else None
        print("\n=== Salón Comunal ===", flush=True)
        print(f"Link para invitados:   {PORT_HINT}/", flush=True)
        print(f"Link de ORGANIZADOR (secreto, no lo compartas): {PORT_HINT}/?organizador={token}\n", flush=True)
        yield
        if task:
            task.cancel()

    app = FastAPI(title="Salón Comunal", lifespan=lifespan)
    app.state.hub = hub
    app.state.organizer_token = token
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/config")
    async def config():
        return {"voz": VOICE_ENABLED}

    @app.get("/api/estado")
    async def estado():
        return hub.room.snapshot()  # vista de invitado (sin pedidos de modo por decidir)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        pid = None
        try:
            first = await ws.receive_json()
            if first.get("action") != "join":
                await ws.send_json({"type": "error", "message": "Primero escribe tu nombre para entrar."})
                await ws.close()
                return
            given = str(first.get("organizer_token") or "")
            is_org = bool(given) and secrets.compare_digest(given, token)
            if given and not is_org:
                await ws.send_json({"type": "error", "message": "El link de organizador no es válido. Entras como invitado."})
            pid = hub.room.add_human(first.get("name", ""), organizer=is_org).id
            hub.sockets[ws] = pid
            hub.room.check_organizer_presence()
            await hub.broadcast()
            summary = hub.room.pop_return_summary(pid)
            if summary:
                await ws.send_json({"type": "return_summary", "summary": summary})
            while True:
                msg = await ws.receive_json()
                try:
                    handle_action(hub.room, pid, msg)
                except (RoomError, KeyError, ValueError) as e:
                    await ws.send_json({"type": "error", "message": str(e)})
                hub.room.check_organizer_presence()
                await hub.broadcast()
                summary = hub.room.pop_return_summary(pid)
                if summary:
                    await ws.send_json({"type": "return_summary", "summary": summary})
        except WebSocketDisconnect:
            pass
        finally:
            hub.sockets.pop(ws, None)
            if pid:
                hub.room.leave(pid)
                hub.room.check_organizer_presence()
                await hub.broadcast()

    return app


app = create_app()
