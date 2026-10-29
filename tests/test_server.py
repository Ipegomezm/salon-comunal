from fastapi.testclient import TestClient

from app.server import build_default_room, create_app


def test_page_and_websocket_flow():
    app = create_app(build_default_room(), run_agents=False)
    with TestClient(app) as client:
        assert "Salón Comunal" in client.get("/").text
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"action": "join", "name": "Felipe"})
            st = ws.receive_json()
            me = st["you"]
            pending = [p for p in st["state"]["participants"] if p["status"] == "pendiente"]
            assert len(pending) == 3
            ws.send_json({"action": "approve_agent", "agent_id": pending[0]["id"]})
            st = ws.receive_json()
            assert any(p["id"] == pending[0]["id"] and p["status"] == "activo" for p in st["state"]["participants"])
            ws.send_json({"action": "say", "text": "Hola salón"})
            st = ws.receive_json()
            assert st["state"]["transcript"][-1]["kind"] in ("mensaje", "turno")
            assert any(e["text"] == "Hola salón" and e["author_id"] == me for e in st["state"]["transcript"])
            ws.send_json({"action": "withdraw_floor"})
            err = ws.receive_json()
            assert err["type"] == "error" and "No habías pedido" in err["message"]
