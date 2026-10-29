"""Captura de la vista de recuadros (etapa 2): un recuadro que pide la palabra
(luz amarilla) y otro que habla (ondas). Opcional, solo para documentar.

Uso (servidor corriendo; usa el link de organizador de la consola):
    python scripts/captura_etapa2.py docs/captura-etapa2.png "http://localhost:8000/?organizador=CLAVE"
"""
import sys
import time

from playwright.sync_api import sync_playwright

out = sys.argv[1] if len(sys.argv) > 1 else "docs/captura-etapa2.png"
url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/"

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 960})
    errores = []
    page.on("pageerror", lambda e: errores.append(str(e)))
    page.goto(url)
    page.fill("#nombre", "Felipe")
    page.click("button[type=submit]")
    page.wait_for_selector("#salon:not([hidden])")
    for _ in range(3):
        page.click("text=Aprobar")
        time.sleep(0.3)
    page.fill("#mensaje", "¿Cómo armamos el grupo de estudio de los jueves?")
    page.click("#form-mensaje button")
    page.wait_for_selector(".recuadro.hablando.tiene", timeout=20000)
    page.wait_for_selector(".recuadro.pide", timeout=20000)
    # Esperar el punto más brillante de la "respiración" (2,6 s por ciclo)
    page.wait_for_function(r"""() => {
        const el = document.querySelector('.recuadro.pide');
        if (!el) return false;
        const m = getComputedStyle(el).boxShadow.match(/0px 0px ([\d.]+)px/);
        return m && parseFloat(m[1]) > 23;
    }""", timeout=10000, polling=50)
    page.screenshot(path=out, full_page=True)
    if errores:
        print("Errores en la página:", errores)
    browser.close()
print("Captura guardada en", out)
