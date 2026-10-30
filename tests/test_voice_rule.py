"""Regla decidida: la voz se reconoce SOLO en la computadora de cada persona.
Nunca se usa la nube (ni Google) como respaldo."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
VOICE_JS = (ROOT / "app" / "static" / "voice.js").read_text(encoding="utf-8")


def _code_only(js: str) -> str:
    """Quita comentarios de una línea para revisar solo el código."""
    return "\n".join(line.split("//", 1)[0] for line in js.splitlines())


def test_no_network_or_cloud_path_in_voice_code():
    code = _code_only(VOICE_JS)
    for banned in ("fetch(", "XMLHttpRequest", "WebSocket", "http://", "https://",
                   "googleapis", "sendBeacon", "processLocally = false", "processLocally: false"):
        assert banned not in code, f"voice.js no debe contener {banned!r}"


def test_every_recognizer_is_forced_local():
    code = _code_only(VOICE_JS)
    news = [m.start() for m in re.finditer(r"new\s+Ctor\s*\(", code)]
    assert len(news) == 1, "solo debe haber un lugar donde se crea el reconocedor"
    after = code[news[0]:news[0] + 300]
    assert "rec.processLocally = true" in after
    assert "if (rec.processLocally !== true) return null" in after
    # available() e install() siempre piden solo local
    assert code.count("processLocally: true") >= 2


@pytest.mark.skipif(shutil.which("node") is None, reason="Node no está instalado")
def test_voice_behavior_never_starts_without_local_processing():
    out = subprocess.run(["node", str(ROOT / "tests" / "js" / "voz_prueba.js")],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "OK voz solo local" in out.stdout


def test_voice_switch_off_by_default(monkeypatch):
    import importlib
    import app.server as server
    monkeypatch.delenv("SALON_VOZ", raising=False)
    importlib.reload(server)
    assert server.VOICE_ENABLED is False
    with TestClient(server.create_app(run_agents=False, token="x")) as c:
        assert c.get("/api/config").json() == {"voz": False}
    monkeypatch.setenv("SALON_VOZ", "1")
    importlib.reload(server)
    assert server.VOICE_ENABLED is True
    with TestClient(server.create_app(run_agents=False, token="x")) as c:
        assert c.get("/api/config").json() == {"voz": True}
    monkeypatch.delenv("SALON_VOZ")
    importlib.reload(server)


def test_no_cloud_speech_code_anywhere_in_app():
    """Ningún archivo de la app llama a servicios de voz en la nube."""
    for path in (ROOT / "app").rglob("*"):
        if path.suffix not in (".py", ".js", ".html"):
            continue
        text = path.read_text(encoding="utf-8").lower()
        for banned in ("googleapis", "speech.googleapis", "api.openai.com", "elevenlabs.io",
                       "deepgram.com", "cognitiveservices"):
            assert banned not in text, f"{path.name} no debe contener {banned}"
