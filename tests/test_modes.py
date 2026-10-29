import pytest

from app.orchestrator import Mode, RoomError
from tests.conftest import run_ticks


def test_normal_mode_by_default(full_room):
    r, felipe, agents = full_room
    assert all(a.mode == Mode.NORMAL for a in agents.values())


def test_fast_mode_request_is_pending_and_not_active(full_room):
    r, felipe, agents = full_room
    rocco = agents["Rocco"]
    req = r.request_fast_mode(rocco.id, "coordinar")
    assert req.status == "pendiente"
    assert rocco.mode == Mode.NORMAL  # negado por defecto mientras nadie decide
    assert any("pide pasar a modo rápido" in e.text for e in r.context.entries)


def test_fast_message_without_authorization_is_blocked(full_room):
    r, felipe, agents = full_room
    rocco = agents["Rocco"]
    r.request_floor(rocco.id)
    with pytest.raises(RoomError):
        r.say(rocco.id, "⟦x·y⟧", mode=Mode.FAST)
    assert "Se bloqueó" in r.context.entries[-1].text


def test_only_humans_authorize(full_room):
    r, felipe, agents = full_room
    rocco, lumi = agents["Rocco"], agents["Lumi"]
    req = r.request_fast_mode(rocco.id, "coordinar")
    with pytest.raises(RoomError):
        r.decide_mode_request(req.id, by=lumi.id, approve=True)
    with pytest.raises(RoomError):
        r.decide_mode_request(req.id, by=rocco.id, approve=True)
    assert rocco.mode == Mode.NORMAL


def test_human_approves_then_revokes(full_room):
    r, felipe, agents = full_room
    rocco = agents["Rocco"]
    req = r.request_fast_mode(rocco.id, "coordinar")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    assert rocco.mode == Mode.FAST
    r.request_floor(rocco.id)
    r.say(rocco.id, "⟦x·y⟧", mode=Mode.FAST)
    assert r.context.entries[-1].mode == "rapido"  # igual queda en la transcripción
    with pytest.raises(RoomError):
        r.decide_mode_request(req.id, by=felipe.id, approve=False)  # ya decidido
    r.back_to_normal(rocco.id, by=felipe.id)
    assert rocco.mode == Mode.NORMAL


def test_deny_keeps_normal(full_room):
    r, felipe, agents = full_room
    rocco = agents["Rocco"]
    req = r.request_fast_mode(rocco.id, "coordinar")
    r.decide_mode_request(req.id, by=felipe.id, approve=False)
    assert req.status == "negado" and rocco.mode == Mode.NORMAL


def test_agent_cannot_change_other_agent_mode(full_room):
    r, felipe, agents = full_room
    rocco, lumi = agents["Rocco"], agents["Lumi"]
    req = r.request_fast_mode(rocco.id, "x")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    with pytest.raises(RoomError):
        r.back_to_normal(rocco.id, by=lumi.id)
    r.back_to_normal(rocco.id, by=rocco.id)  # sí puede volver por su cuenta
    assert rocco.mode == Mode.NORMAL


def test_loophole_report_visible(full_room):
    r, felipe, agents = full_room
    r.report_loophole(agents["Tina"].id, "frases muy cortas")
    e = r.context.entries[-1]
    assert e.kind == "vacio" and "frases muy cortas" in e.text


def test_autonomous_work(full_room):
    r, felipe, agents = full_room
    tina = agents["Tina"]
    with pytest.raises(RoomError):
        r.start_autonomous(tina.id, "plan", by=agents["Lumi"].id)  # solo personas
    r.start_autonomous(tina.id, "armar el plan", by=felipe.id)
    assert tina.autonomous
    r.speak_now(felipe.id, "¿Ideas para la fiesta?")
    run_ticks(r)
    assert not any(e.author_id == tina.id and e.kind == "mensaje" for e in r.context.entries)
    r.end_autonomous(tina.id, by=felipe.id)
    run_ticks(r)
    last_tina = [e for e in r.context.entries if e.author_id == tina.id and e.kind == "mensaje"]
    assert last_tina and "armar el plan" in last_tina[-1].text


def test_mock_agents_request_fast_mode_and_report_loophole(full_room):
    r, felipe, agents = full_room
    r.speak_now(felipe.id, "Necesito que sean más rápidos, ¿hay algún truco?")
    run_ticks(r)
    reqs = list(r.mode_requests.values())
    assert len(reqs) == 1 and reqs[0].agent_id == agents["Rocco"].id
    assert agents["Rocco"].mode == Mode.NORMAL
    assert any(e.kind == "vacio" and e.author_id == agents["Tina"].id for e in r.context.entries)
