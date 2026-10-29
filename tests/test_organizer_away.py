"""Qué pasa mientras no hay un organizador conectado (con reloj falso)."""
import pytest

from app.agents.mock import make_mock
from app.orchestrator import Mode, RoomError, Status
from app.orchestrator.room import DEFAULT_AGENT_COOLDOWN_SECONDS, DEFAULT_AGENT_TURN_BUDGET, Room


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make_room(clock, **kw):
    r = Room(clock=clock, **kw)
    felipe = r.add_human("Felipe", organizer=True)
    ana = r.add_human("Ana")
    agents = {}
    for style in ("creativa", "critica", "practica"):
        a = r.add_agent(make_mock(style), added_by=felipe.id)
        r.approve_agent(a.id, by=felipe.id)
        agents[a.name] = a
    r.check_organizer_presence()
    return r, felipe, ana, agents


def run(r, clock, seconds, step=1.0):
    end = clock.t + seconds
    while clock.t < end:
        clock.t += step
        r.check_organizer_presence()
        r.agent_tick()


def agent_msgs(r):
    return [e for e in r.context.entries if e.kind == "mensaje" and e.author_kind == "agente"]


def test_defaults():
    r = Room()
    assert r.agent_cooldown_seconds == DEFAULT_AGENT_COOLDOWN_SECONDS == 8
    assert r.agent_turn_budget == DEFAULT_AGENT_TURN_BUDGET == 6


# 1) Los agentes siguen hablando solos, en modo normal, con frenos.

def test_agents_keep_talking_while_organizer_away():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.speak_now(felipe.id, "¿Cómo armamos el grupo de estudio?")
    r.leave(felipe.id)
    run(r, clock, 50)
    msgs = agent_msgs(r)
    assert len(msgs) > 3                                  # se responden entre ellos
    assert any("Lumi" in e.text or "Rocco" in e.text or "Tina" in e.text for e in msgs)
    assert all(e.mode == "normal" for e in msgs)
    assert not r.paused


def test_agent_never_answers_itself_and_budget_caps_chain():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock, agent_turn_budget=4, agent_cooldown_seconds=0)
    r.speak_now(felipe.id, "Hola a todos")
    run(r, clock, 40)
    msgs = agent_msgs(r)
    assert len(msgs) == 4                                 # tope de turnos
    for a, b in zip(msgs, msgs[1:]):
        assert a.author_id != b.author_id                 # nadie se responde a sí mismo
    assert r.turns.queue == [] and r.turns.speaker is None
    r.speak_now(ana.id, "Sigamos")                        # una persona habla: se recarga el tope
    run(r, clock, 40)
    assert len(agent_msgs(r)) == 8


def test_cooldown_spaces_out_each_agent():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock, agent_cooldown_seconds=20, agent_turn_budget=50)
    r.speak_now(felipe.id, "Hola")
    run(r, clock, 60)
    # con 20 s de espera, en 60 s cada agente habla como mucho 3 veces
    spoke = {}
    for e in agent_msgs(r):
        spoke.setdefault(e.author_id, 0)
        spoke[e.author_id] += 1
    assert max(spoke.values()) <= 3


def test_fast_mode_agents_return_to_normal_when_organizer_leaves():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    rocco = agents["Rocco"]
    req = r.request_fast_mode(rocco.id, "x")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    assert rocco.mode == Mode.FAST
    r.leave(felipe.id)
    r.check_organizer_presence()
    assert rocco.mode == Mode.NORMAL
    assert "no hay un organizador conectado" in r.context.entries[-1].text


def test_human_addressing_one_agent_keeps_others_quiet():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock, agent_cooldown_seconds=0)
    r.speak_now(felipe.id, "Rocco, ¿qué riesgos ves?")
    run(r, clock, 20)
    authors = {e.author_name for e in agent_msgs(r)}
    assert authors == {"Rocco"}


# 2) Agentes nuevos y modo rápido quedan pendientes hasta que decida una persona organizadora.

def test_pending_items_wait_for_human_organizer():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.leave(felipe.id)
    r.check_organizer_presence()
    newbie = r.add_agent(make_mock("creativa", "Nico"), added_by=ana.id)
    req = r.request_fast_mode(agents["Rocco"].id, "coordinar")
    with pytest.raises(RoomError):
        r.approve_agent(newbie.id, by=ana.id)
    with pytest.raises(RoomError):
        r.decide_mode_request(req.id, by=ana.id, approve=True)
    run(r, clock, 30)
    assert newbie.status == Status.PENDING and req.status == "pendiente"
    assert agents["Rocco"].mode == Mode.NORMAL


# 3) Reportes de vacíos marcados para el organizador.

def test_loophole_reports_are_flagged_for_organizer():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.report_loophole(agents["Tina"].id, "frases cortas")
    snap_org = r.snapshot(viewer=felipe.id)
    assert len(snap_org["flags"]) == 1 and snap_org["flags"][0]["author"] == "Tina"
    assert r.snapshot(viewer=ana.id)["flags"] == []
    with pytest.raises(RoomError):
        r.acknowledge_flag(snap_org["flags"][0]["id"], by=ana.id)
    r.acknowledge_flag(snap_org["flags"][0]["id"], by=felipe.id)
    assert r.snapshot(viewer=felipe.id)["flags"] == []
    assert any(e.kind == "vacio" for e in r.context.entries)   # sigue en la transcripción


# 4) Resumen al volver.

def test_return_summary():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.speak_now(felipe.id, "¿Ideas para la fiesta?")
    run(r, clock, 5)
    r.leave(felipe.id)
    r.check_organizer_presence()
    clock.t += 1
    r.speak_now(ana.id, "Necesito que vayan más rápido, ¿hay algún truco?")
    r.add_agent(make_mock("creativa", "Nico"), added_by=ana.id)
    run(r, clock, 80)                                       # pasa el minuto: se pausa
    assert r.paused
    felipe2 = r.add_human("Felipe", organizer=True)
    r.check_organizer_presence()
    s = r.pop_return_summary(felipe2.id)
    assert s is not None
    assert s["paused"] is True
    assert any(m["author"] == "Ana" for m in s["messages"])
    assert "Nico" in s["pending_agents"]
    assert any(m["agent"] == "Rocco" for m in s["pending_mode_requests"])
    assert len(s["flags"]) == 1 and s["flags"][0]["author"] == "Tina"
    text = " ".join(s["lines"])
    assert "Estuviste fuera" in text and "Nico" in text and "Rocco" in text
    assert r.pop_return_summary(felipe2.id) is None         # se entrega una sola vez
    assert r.pop_return_summary(ana.id) is None             # solo al organizador


def test_no_summary_on_quick_reload_with_nothing_new():
    clock = FakeClock()
    r = Room(clock=clock)
    felipe = r.add_human("Felipe", organizer=True)
    r.check_organizer_presence()
    r.leave(felipe.id)
    r.check_organizer_presence()
    clock.t += 3
    f2 = r.add_human("Felipe", organizer=True)
    r.check_organizer_presence()
    assert r.pop_return_summary(f2.id) is None


def test_no_summary_on_first_entry():
    clock = FakeClock()
    r = Room(clock=clock)
    r.add_agent(make_mock("creativa"))
    clock.t = 30
    r.check_organizer_presence()
    f = r.add_human("Felipe", organizer=True)
    r.check_organizer_presence()
    assert r.pop_return_summary(f.id) is None
