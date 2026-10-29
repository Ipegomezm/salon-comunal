"""Captura del recuadro de Felipe en «Baño» (reloj naranja) mientras los agentes conversan.
Opcional, solo para documentar. Para ver el reloj naranja rápido, prende el servidor con un
límite corto, por ejemplo:  SALON_LIMITE_BANO=320 uvicorn app.server:app

Uso:
    python scripts/captura_bano.py docs/captura-bano.png "http://localhost:8000/?organizador=CLAVE"
"""
import sys
import time

from playwright.sync_api import sync_playwright

out = sys.argv[1] if len(sys.argv) > 1 else "docs/captura-bano.png"
url = sys.argv[2]

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 960})
    page.goto(url)
    page.fill("#nombre", "Felipe")
    page.click("#form-entrar button")
    page.wait_for_selector("#salon:not([hidden])")
    for _ in range(3):
        page.click("text=Aprobar")
        time.sleep(0.3)
    page.fill("#mensaje", "Voy un momento al baño. Mientras tanto, ¿cómo armamos el grupo de estudio?")
    page.click("#form-mensaje button")
    time.sleep(0.5)
    page.click("#btn-bano")
    page.wait_for_selector(".recuadro.bano .reloj.naranja", timeout=60000)
    page.wait_for_selector(".recuadro.hablando", timeout=30000)
    time.sleep(0.4)
    page.screenshot(path=out, full_page=True)
    browser.close()
print("Captura guardada en", out)
