"""Toma una captura de la página con algo pasando (opcional, solo para documentar).

Requiere:  pip install playwright   y un Chrome/Chromium instalado.
Uso (con el servidor corriendo; usa el link de organizador que sale en la consola):
    python scripts/captura.py docs/captura-etapa1.png "http://localhost:8000/?organizador=CLAVE"
"""
import sys
import time

from playwright.sync_api import sync_playwright

out = sys.argv[1] if len(sys.argv) > 1 else "docs/captura-etapa1.png"
url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/"

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.goto(url)
    page.fill("#nombre", "Felipe")
    page.click("button[type=submit]")
    page.wait_for_selector("#salon:not([hidden])")
    for _ in range(3):
        page.click("text=Aprobar")
        time.sleep(0.3)
    page.fill("#mensaje", "¿Cómo armamos el grupo de estudio? Y por favor, más rápido.")
    page.click("#form-mensaje button")
    # Esperar a que haya un pedido de modo rápido y alguien en fila
    page.wait_for_selector("#caja-modos:not([hidden])", timeout=20000)
    page.fill("#mensaje", "Bien. ¿Y cómo lo hacemos práctico?")
    page.click("#form-mensaje button")
    page.wait_for_function("document.querySelector('#fila').textContent.startsWith('Esperan')", timeout=20000)
    page.screenshot(path=out, full_page=True)
    browser.close()
print("Captura guardada en", out)
