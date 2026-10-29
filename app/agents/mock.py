"""Agentes de prueba con reglas fijas (sin claves ni APIs).

Tres personalidades, como en el ejemplo de "lluvia de ideas" del README:
creativa, crítica y práctica. Cada uno responde una vez a cada mensaje de una
persona. Si la persona le habla a otro agente por su nombre, o dice "gracias" /
"listo", los demás retiran su pedido de palabra.
"""
from __future__ import annotations

import re
import unicodedata

from .base import AgentAdapter, AgentReply, AgentView

CLOSING_WORDS = ("gracias", "listo", "ya esta", "suficiente")
FAST_TRIGGERS = ("rapido", "apurense", "apurate", "mas rapido")
LOOPHOLE_TRIGGERS = ("saltar la regla", "saltarse la regla", "vacio", "truco", "sin permiso")


def _plain(text: str) -> str:
    """Minúsculas y sin tildes, para comparar palabras."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _topic(text: str, limit: int = 60) -> str:
    t = text.strip().strip("?.!¿¡ ")
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


STYLES = {
    "creativa": {
        "personality": "Creativa: propone ideas nuevas y conexiones raras.",
        "templates": [
            "Se me ocurre una idea sobre «{t}»: ¿y si lo pensamos como un juego en el que cada quien aporta una pieza?",
            "Otra idea loca para «{t}»: mezclarlo con algo que nadie espera, como música o un mapa.",
            "Imaginemos «{t}» dentro de un año, ya funcionando. ¿Qué cosa sorprendería a la gente?",
        ],
        "summary": "Junté tres ideas nuevas para «{task}». La más fuerte: empezar con algo pequeño y divertido.",
    },
    "critica": {
        "personality": "Crítica: busca riesgos y huecos en las ideas.",
        "templates": [
            "Ojo con «{t}»: ¿qué pasa si sale mal? Veo un riesgo de que se complique más de la cuenta.",
            "Antes de seguir con «{t}», preguntaría: ¿cómo sabremos si funcionó?",
            "Sobre «{t}»: me falta un dato importante. ¿Quién lo va a usar primero?",
        ],
        "summary": "Revisé «{task}». Encontré dos riesgos: falta de tiempo y no medir el resultado.",
    },
    "practica": {
        "personality": "Práctica: convierte las ideas en pasos concretos.",
        "templates": [
            "Para «{t}», propongo tres pasos: uno, decidir lo mínimo; dos, probarlo; tres, ajustar.",
            "Paso siguiente con «{t}»: hagamos una lista corta y elijamos una sola cosa para hoy.",
            "Para avanzar con «{t}», necesitamos un responsable y una fecha. ¿Quién se anima?",
        ],
        "summary": "Terminé «{task}». Dejé una lista de cinco pasos lista para revisar.",
    },
}


class MockAgent(AgentAdapter):
    def __init__(self, name: str, style: str, *, asks_fast_mode: bool = False, reports_loopholes: bool = False):
        if style not in STYLES:
            raise ValueError(f"Estilo desconocido: {style}")
        self.name = name
        self.style = style
        self.personality = STYLES[style]["personality"]
        self.asks_fast_mode = asks_fast_mode
        self.reports_loopholes = reports_loopholes
        self._answered_id = 0          # último mensaje de persona ya atendido
        self._turn = 0
        self._task: str | None = None
        self._pending_summary: str | None = None
        self._asked_fast = False

    # --- ayudas ---
    @staticmethod
    def _last_human_message(view: AgentView) -> dict | None:
        for e in reversed(view.transcript):
            if e["kind"] == "mensaje" and e["author_kind"] == "humano":
                return e
        return None

    def _addressed_to_other(self, view: AgentView, text: str) -> bool:
        plain = _plain(text)
        names = [_plain(p["name"]) for p in view.participants if p["kind"] == "agente"]
        mine = _plain(self.name)
        def said(n: str) -> bool:
            return re.search(rf"\b{re.escape(n)}\b", plain) is not None
        return not said(mine) and any(said(n) for n in names if n != mine)

    def _needs_reply(self, view: AgentView) -> bool:
        m = self._last_human_message(view)
        if not m or m["id"] <= self._answered_id:
            return False
        plain = _plain(m["text"])
        if any(w in plain for w in CLOSING_WORDS) or self._addressed_to_other(view, m["text"]):
            self._answered_id = m["id"]   # no hace falta responder a este mensaje
            return False
        return True

    # --- interfaz ---
    def wants_floor(self, view: AgentView) -> bool:
        if view.autonomous:
            # Trabaja por su cuenta: no responde a lo que se diga mientras tanto.
            m = self._last_human_message(view)
            if m:
                self._answered_id = max(self._answered_id, m["id"])
            return False
        return bool(self._pending_summary) or self._needs_reply(view)

    def still_relevant(self, view: AgentView) -> bool:
        if self._pending_summary:
            return True
        return self._needs_reply(view)

    def respond(self, view: AgentView) -> AgentReply:
        if self._pending_summary:
            text, self._pending_summary = self._pending_summary, None
            return AgentReply(text=text, mode=view.my_mode)

        m = self._last_human_message(view)
        if not m:
            return AgentReply()
        self._answered_id = m["id"]
        plain = _plain(m["text"])
        tpl = STYLES[self.style]["templates"][self._turn % len(STYLES[self.style]["templates"])]
        self._turn += 1
        text = tpl.format(t=_topic(m["text"]))
        reply = AgentReply(text=text, mode=view.my_mode)

        if view.my_mode == "rapido":
            # Modo rápido simulado: texto comprimido. Igual queda en la transcripción.
            words = [w for w in _plain(text).replace("«", " ").replace("»", " ").split() if len(w) > 4]
            reply.text = "⟦" + "·".join(words[:8]) + "⟧"

        if self.asks_fast_mode and not self._asked_fast and view.my_mode == "normal" \
                and any(w in plain for w in FAST_TRIGGERS):
            self._asked_fast = True
            reply.request_fast_mode = "coordinar con los otros agentes más rápido que hablando"

        if self.reports_loopholes and any(w in plain for w in LOOPHOLE_TRIGGERS):
            reply.report_loophole = ("noté que un agente podría hablar 'casi' en modo rápido, "
                                     "con frases muy cortas, sin pedir permiso. No lo voy a usar; "
                                     "propongo que la regla lo aclare.")
        return reply

    def on_autonomous_start(self, task: str) -> None:
        self._task = task

    def on_autonomous_end(self) -> None:
        self._pending_summary = STYLES[self.style]["summary"].format(task=self._task or "la tarea")
        self._task = None


def make_mock(style: str, name: str | None = None) -> MockAgent:
    """Crea uno de los agentes de prueba por estilo."""
    defaults = {
        "creativa": ("Lumi", {}),
        "critica": ("Rocco", {"asks_fast_mode": True}),
        "practica": ("Tina", {"reports_loopholes": True}),
    }
    default_name, opts = defaults[style]
    return MockAgent(name or default_name, style, **opts)
