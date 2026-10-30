"""Captura del resumen que ve el organizador al volver. Opcional, solo para documentar.

Uso (servidor corriendo; usa el link de organizador de la consola):
    python scripts/captura_resumen.py docs/captura-resumen-al-volver.png "http://localhost:8000/?organizador=CLAVE"
"""
import sys
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

out = sys.argv[1] if len(sys.argv) > 1 else "docs/captura-resumen-al-volver.png"
org_url = sys.argv[2]
base = "{0.scheme}://{0.netloc}/".format(urlsplit(org_url))


def entrar(page, url, nombre):
    page.goto(url)
    page.fill("#nombre", nombre)
    page.click("#form-entrar button")
    page.wait_for_selector("#salon:not([hidden])")


with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    org = browser.new_page(viewport={"width": 1366, "height": 1000})
    entrar(org, org_url, "Felipe")
    for _ in range(3):
        org.click("text=Aprobar")
        time.sleep(0.3)
    org.fill("#mensaje", "¿Cómo armamos el grupo de estudio?")
    org.click("#form-mensaje button")
    org.fill("#nombre-agente", "Nico")            # solo la persona organizadora agrega agentes
    org.click("#form-agente button")
    time.sleep(2)
    org.close()                                   # Felipe se va

    ana = browser.new_page(viewport={"width": 1366, "height": 900})
    entrar(ana, base, "Ana")
    ana.fill("#mensaje", "Necesito que vayan más rápido, ¿hay algún truco?")
    ana.click("#form-mensaje button")
    time.sleep(20)                                # los agentes siguen conversando

    org2 = browser.new_page(viewport={"width": 1366, "height": 1000})
    entrar(org2, org_url, "Felipe")               # Felipe vuelve
    org2.wait_for_selector("#resumen:not([hidden])", timeout=10000)
    org2.click("#resumen-detalle summary")
    time.sleep(0.5)
    org2.screenshot(path=out, full_page=True)
    browser.close()
print("Captura guardada en", out)
