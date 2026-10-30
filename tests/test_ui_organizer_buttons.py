"""Prueba de la página (Playwright): los 4 botones de agentes solo se ven como persona organizadora.
Se salta si Playwright o un navegador no están instalados (son opcionales)."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parent.parent
TOKEN = "clave-de-prueba-ui"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = dict(os.environ, SALON_ORGANIZER_TOKEN=TOKEN, SALON_TICK="60", SALON_VOZ="0")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.server:app", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = None
        for kw in ({"channel": "chrome"}, {}):
            try:
                b = p.chromium.launch(**kw)
                break
            except Exception:
                continue
        if b is None:
            pytest.skip("No hay navegador para Playwright")
        yield b
        b.close()


def _enter(page, url, name):
    page.goto(url)
    page.fill("#nombre", name)
    page.click("#form-entrar button")
    page.wait_for_selector("#salon:not([hidden])")


def test_buttons_visible_only_for_person_organizer(server, browser):
    org = browser.new_page()
    _enter(org, f"{server}/?organizador={TOKEN}", "Felipe")
    for _ in range(3):
        org.click("text=Aprobar")
        org.wait_for_timeout(200)
    org.wait_for_selector("text=Mandar a trabajar solo")
    assert org.is_visible("#caja-agregar")
    assert org.locator("text=Mandar a trabajar solo").count() == 3

    guest = browser.new_page()
    _enter(guest, server, "Ana")
    guest.wait_for_selector("#participantes li")
    guest.wait_for_timeout(300)
    assert not guest.is_visible("#caja-agregar")
    for label in ("Mandar a trabajar solo", "Pedir que vuelva", "Volver a modo normal", "Agregar"):
        assert guest.locator(f"button:visible:has-text('{label}')").count() == 0, label

    # Felipe en «Baño»: también se esconden
    org.click("#btn-bano")
    org.wait_for_selector("text=Ya volví")
    org.wait_for_timeout(300)
    assert not org.is_visible("#caja-agregar")
    assert org.locator("button:visible:has-text('Mandar a trabajar solo')").count() == 0
    org.close()
    guest.close()
