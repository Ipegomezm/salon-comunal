"""Capturas para docs/GUIA-PRUEBA.md: la pantalla de entrada y la de aprobar agentes.
Opcional, solo para documentar.

Uso:
    python scripts/captura_guia.py "http://localhost:8000/?organizador=CLAVE"
"""
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1]
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 520})
    page.goto(url)
    page.fill("#nombre", "Felipe")
    page.screenshot(path="docs/captura-entrar.png")
    page.set_viewport_size({"width": 1366, "height": 760})
    page.click("#form-entrar button")
    page.wait_for_selector("text=Aprobar")
    page.screenshot(path="docs/captura-aprobar.png")
    browser.close()
print("Capturas guardadas: docs/captura-entrar.png y docs/captura-aprobar.png")
