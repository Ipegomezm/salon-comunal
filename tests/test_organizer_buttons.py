"""Los 4 botones de agentes son solo para una PERSONA organizadora (Felipe):
mandar a trabajar solo, pedir que vuelva, agregar agente de prueba, volver a modo normal."""
import pytest
from fastapi.testclient import TestClient

from app.agents.mock import make_mock
from app.orchestrator import Mode, RoomError, Status
from app.server import build_default_room, create_app


@pytest.fixture
def setup(room):
    felipe = room.add_human("Felipe", organizer=True)
    ana = room.add_human("Ana")
    agents = {}
    for style in ("creativa", "critica", "practica"):
        a = room.add_agent(make_mock(style), added_by=felipe.id)
        room.approve_agent(a.id, by=felipe.id)
        agents[a.name] = a
    room.grant_organizer(agents["Lumi"].id, by=felipe.id)   # Lumi: agente organizador
    return room, felipe, ana, agents


def _snapshot_state(r):
    return [(p.id, p.status, p.mode, p.autonomous) for p in r.registry.all()], len(r.registry.all())


def test_person_organizer_can_use_all_four(setup):
    r, felipe, ana, agents = setup
    rocco = agents["Rocco"]
    nico = r.add_agent(make_mock("creativa", "Nico"), added_by=felipe.id)      # 3) agregar
    assert nico.status == Status.PENDING
    r.start_autonomous(rocco.id, "plan", by=felipe.id)                          # 1) trabajar solo
    r.end_autonomous(rocco.id, by=felipe.id)                                    # 2) que vuelva
    req = r.request_fast_mode(rocco.id, "x")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    r.back_to_normal(rocco.id, by=felipe.id)                                    # 4) modo normal
    assert rocco.mode == Mode.NORMAL and not rocco.autonomous


@pytest.mark.parametrize("who", ["ana", "lumi_organizer", "tina"])
def test_everyone_else_is_refused_and_nothing_changes(setup, who):
    r, felipe, ana, agents = setup
    rocco = agents["Rocco"]
    req = r.request_fast_mode(rocco.id, "x")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    r.start_autonomous(agents["Tina"].id if who != "tina" else rocco.id, "algo", by=felipe.id)
    actor = {"ana": ana, "lumi_organizer": agents["Lumi"], "tina": agents["Tina"]}[who].id
    target_auto = agents["Tina"] if who != "tina" else rocco
    before = _snapshot_state(r)
    with pytest.raises(RoomError):
        r.start_autonomous(rocco.id if who != "tina" else agents["Lumi"].id, "plan", by=actor)
    with pytest.raises(RoomError):
        r.end_autonomous(target_auto.id, by=actor)
    with pytest.raises(RoomError):
        r.add_agent(make_mock("creativa", "Nico"), added_by=actor)
    with pytest.raises(RoomError):
        r.back_to_normal(rocco.id, by=actor)
    assert _snapshot_state(r) == before


def test_agent_organizer_gets_clear_message(setup):
    r, felipe, ana, agents = setup
    with pytest.raises(RoomError, match="Solo una persona organizadora"):
        r.add_agent(make_mock("creativa", "Nico"), added_by=agents["Lumi"].id)
    with pytest.raises(RoomError, match="Solo el organizador"):
        r.add_agent(make_mock("creativa", "Nico"), added_by=ana.id)


def test_organizer_on_bano_is_refused(setup):
    r, felipe, ana, agents = setup
    r.step_away(felipe.id)
    with pytest.raises(RoomError):
        r.start_autonomous(agents["Rocco"].id, "plan", by=felipe.id)
    with pytest.raises(RoomError):
        r.add_agent(make_mock("creativa", "Nico"), added_by=felipe.id)


def test_agent_can_still_return_by_itself_and_go_back_to_normal(setup):
    """Volver por su cuenta no es un botón: el propio agente sí puede."""
    r, felipe, ana, agents = setup
    rocco = agents["Rocco"]
    r.start_autonomous(rocco.id, "plan", by=felipe.id)
    r.end_autonomous(rocco.id, by=rocco.id)
    assert not rocco.autonomous
    req = r.request_fast_mode(rocco.id, "x")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    r.back_to_normal(rocco.id, by=rocco.id)
    assert rocco.mode == Mode.NORMAL


def test_room_can_still_add_agents_without_a_person(room):
    a = room.add_agent(make_mock("creativa"))    # el salón (al arrancar) los agrega como pendientes
    assert a.status == Status.PENDING


def test_snapshot_flag(setup):
    r, felipe, ana, agents = setup
    assert r.snapshot(viewer=felipe.id)["you_can_manage_agents"] is True
    assert r.snapshot(viewer=ana.id)["you_can_manage_agents"] is False
    assert r.snapshot(viewer=agents["Lumi"].id)["you_can_manage_agents"] is False


# --- Servidor: un invitado manda las acciones a mano y se rechazan ---

def _join(ws, name, token=None):
    msg = {"action": "join", "name": name}
    if token:
        msg["organizer_token"] = token
    ws.send_json(msg)


def _state(ws):
    while True:
        m = ws.receive_json()
        if m["type"] == "state":
            return m


def test_server_refuses_guest_for_all_four():
    room = build_default_room()
    app = create_app(room, run_agents=False, token="clave-de-prueba")
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as org:
            _join(org, "Felipe", "clave-de-prueba")
            st = _state(org)
            felipe_id = st["you"]
            for p in st["state"]["participants"]:
                if p["status"] == "pendiente":
                    org.send_json({"action": "approve_agent", "agent_id": p["id"]})
                    _state(org)
            agents = [p for p in room.registry.active_agents()]
            rocco = agents[1]
            room.start_autonomous(agents[2].id, "algo", by=felipe_id)
            req = room.request_fast_mode(rocco.id, "x")
            room.decide_mode_request(req.id, by=felipe_id, approve=True)
            with client.websocket_connect("/ws") as guest:
                _join(guest, "Ana")
                _state(guest)
                before = (len(room.registry.all()), rocco.mode, rocco.autonomous, agents[2].autonomous)
                for msg in (
                    {"action": "start_autonomous", "agent_id": rocco.id, "task": "x"},
                    {"action": "end_autonomous", "agent_id": agents[2].id},
                    {"action": "add_agent", "style": "creativa", "name": "Nico"},
                    {"action": "back_to_normal", "agent_id": rocco.id},
                ):
                    guest.send_json(msg)
                    err = guest.receive_json()
                    assert err["type"] == "error" and "organizador" in err["message"], msg
                    _state(guest)
                after = (len(room.registry.all()), rocco.mode, rocco.autonomous, agents[2].autonomous)
                assert before == after
                assert guest_view_flag(room, guest) is False


def guest_view_flag(room, ws):
    ws.send_json({"action": "noop"})
    ws.receive_json()          # error: acción desconocida
    return _state(ws)["state"]["you_can_manage_agents"]
