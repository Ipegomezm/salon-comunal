"""Servidor web: página + WebSocket. Corre con:  uvicorn app.server:app --reload"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents.mock import make_mock
from app.orchestrator import Room, RoomError

STATIC = Path(__file__).parent / "static"
TICK_SECONDS = float(os.environ.get("SALON_TICK", "1.5"))  # pausa entre pasos de los agentes


def build_default_room() -> Room:
    """Salón de prueba con tres agentes que esperan aprobación."""
    room = Room()
    for style in ("creativa", "critica", "practica"):
        room.add_agent(make_mock(style))
    return room


class Hub:
    """Conexiones abiertas de las personas y envío del estado a todos."""

    def __init__(self, room: Room) -> None:
        self.room = room
        self.sockets: dict[WebSocket, str] = {}

    async def broadcast(self) -> None:
        state = self.room.snapshot()
        for ws, pid in list(self.sockets.items()):
            try:
                await ws.send_json({"type": "state", "you": pid, "state": state})
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
    elif a == "add_agent":
        style = msg.get("style", "creativa")
        if style not in ("creativa", "critica", "practica"):
            raise RoomError("Tipo de agente desconocido.")
        room.add_agent(make_mock(style, (msg.get("name") or "").strip() or None), added_by=pid)
    else:
        raise RoomError("Acción desconocida.")


def create_app(room: Room | None = None, run_agents: bool = True) -> FastAPI:
    hub = Hub(room or build_default_room())

    async def agent_loop() -> None:
        while True:
            await asyncio.sleep(TICK_SECONDS)
            try:
                if hub.room.agent_tick():
                    await hub.broadcast()
            except Exception as e:  # no tumbar el servidor por un agente
                print("Error en agentes:", e)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(agent_loop()) if run_agents else None
        yield
        if task:
            task.cancel()

    app = FastAPI(title="Salón Comunal", lifespan=lifespan)
    app.state.hub = hub
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/estado")
    async def estado():
        return hub.room.snapshot()

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
            pid = hub.room.add_human(first.get("name", "")).id
            hub.sockets[ws] = pid
            await hub.broadcast()
            while True:
                msg = await ws.receive_json()
                try:
                    handle_action(hub.room, pid, msg)
                except (RoomError, KeyError, ValueError) as e:
                    await ws.send_json({"type": "error", "message": str(e)})
                await hub.broadcast()
        except WebSocketDisconnect:
            pass
        finally:
            hub.sockets.pop(ws, None)
            if pid:
                hub.room.leave(pid)
                await hub.broadcast()

    return app


app = create_app()
