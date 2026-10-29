from fastapi.testclient import TestClient

from app.server import build_default_room, create_app

TOKEN = "clave-de-prueba"


def _join(ws, name, token=None):
    msg = {"action": "join", "name": name}
    if token is not None:
        msg["organizer_token"] = token
    ws.send_json(msg)


def _state(ws):
    while True:
        m = ws.receive_json()
        if m["type"] == "state":
            return m


def test_organizer_flow_with_token():
    app = create_app(build_default_room(), run_agents=False, token=TOKEN)
    with TestClient(app) as client:
        assert "Salón Comunal" in client.get("/").text
        with client.websocket_connect("/ws") as ws:
            _join(ws, "Felipe", TOKEN)
            st = _state(ws)
            assert st["state"]["you_are_organizer"] is True
            assert st["state"]["you_can_decide_fast_mode"] is True
            pending = [p for p in st["state"]["participants"] if p["status"] == "pendiente"]
            assert len(pending) == 3
            ws.send_json({"action": "approve_agent", "agent_id": pending[0]["id"]})
            st = _state(ws)
            assert any(p["id"] == pending[0]["id"] and p["status"] == "activo" for p in st["state"]["participants"])
            ws.send_json({"action": "say", "text": "Hola salón"})
            st = _state(ws)
            assert any(e["text"] == "Hola salón" and e["author_id"] == st["you"] for e in st["state"]["transcript"])
            ws.send_json({"action": "withdraw_floor"})
            err = ws.receive_json()
            assert err["type"] == "error" and "No habías pedido" in err["message"]


def test_guest_cannot_approve_even_by_sending_the_action():
    app = create_app(build_default_room(), run_agents=False, token=TOKEN)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            _join(ws, "Felipe")  # mismo nombre, sin clave: invitado
            st = _state(ws)
            assert st["state"]["you_are_organizer"] is False
            assert st["state"]["you_can_decide_fast_mode"] is False
            pending = [p for p in st["state"]["participants"] if p["status"] == "pendiente"]
            ws.send_json({"action": "approve_agent", "agent_id": pending[0]["id"]})
            err = ws.receive_json()
            assert err["type"] == "error" and "organizador" in err["message"]
            st = _state(ws)
            assert all(p["status"] == "pendiente" for p in st["state"]["participants"] if p["kind"] == "agente")


def test_wrong_token_enters_as_guest():
    app = create_app(build_default_room(), run_agents=False, token=TOKEN)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            _join(ws, "Felipe", "clave-falsa")
            err = ws.receive_json()
            assert err["type"] == "error"
            st = _state(ws)
            assert st["state"]["you_are_organizer"] is False


def test_grant_organizer_is_not_exposed_over_websocket():
    app = create_app(build_default_room(), run_agents=False, token=TOKEN)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            _join(ws, "Felipe", TOKEN)
            st = _state(ws)
            ws.send_json({"action": "grant_organizer", "target": st["you"]})
            err = ws.receive_json()
            assert err["type"] == "error" and "desconocida" in err["message"]


def test_organizer_gets_summary_on_return():
    app = create_app(build_default_room(), run_agents=False, token=TOKEN)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as guest:
            _join(guest, "Ana")
            _state(guest)
            with client.websocket_connect("/ws") as org:
                _join(org, "Felipe", TOKEN)
                _state(org)
            guest.send_json({"action": "say", "text": "Hola, ¿hay alguien?"})
            with client.websocket_connect("/ws") as org:
                _join(org, "Felipe", TOKEN)
                got = None
                for _ in range(5):
                    m = org.receive_json()
                    if m["type"] == "return_summary":
                        got = m["summary"]
                        break
                assert got is not None
                assert any(x["author"] == "Ana" for x in got["messages"])
                assert len(got["pending_agents"]) == 3


def test_bano_over_websocket():
    app = create_app(build_default_room(), run_agents=False, token=TOKEN)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as org:
            _join(org, "Felipe", TOKEN)
            st = _state(org)
            pending = [p for p in st["state"]["participants"] if p["status"] == "pendiente"]
            org.send_json({"action": "step_away"})
            st = _state(org)
            me = next(p for p in st["state"]["participants"] if p["id"] == st["you"])
            assert me["away"] is True and me["away_seconds"] is not None
            assert st["state"]["paused"] is False
            org.send_json({"action": "approve_agent", "agent_id": pending[0]["id"]})
            err = org.receive_json()
            assert err["type"] == "error" and "Ya volví" in err["message"]
            _state(org)
            org.send_json({"action": "come_back"})
            _state(org)
            m = org.receive_json()
            assert m["type"] == "return_summary"
