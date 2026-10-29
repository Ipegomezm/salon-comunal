"""Botón «Baño»: alejarse un rato con la página abierta (con reloj falso)."""
import pytest

from app.agents.mock import make_mock
from app.orchestrator import Mode, RoomError, Status
from app.orchestrator.room import DEFAULT_BATHROOM_LIMIT_SECONDS, Room


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


def test_default_limit_is_25_minutes():
    assert DEFAULT_BATHROOM_LIMIT_SECONDS == 1500
    assert Room().bathroom_limit == 1500


def test_step_away_and_back_are_logged():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.step_away(ana.id)
    assert ana.away and "Ana se fue un rato." == r.context.entries[-1].text
    with pytest.raises(RoomError):
        r.step_away(ana.id)
    r.come_back(ana.id)
    assert not ana.away and "Ana volvió." == r.context.entries[-1].text
    with pytest.raises(RoomError):
        r.come_back(ana.id)


def test_agents_cannot_use_bano():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    with pytest.raises(RoomError):
        r.step_away(agents["Lumi"].id)


def test_person_away_cannot_take_floor():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.request_floor(ana.id)              # tiene la palabra
    r.step_away(ana.id)                  # al irse la suelta
    assert r.turns.speaker != ana.id
    with pytest.raises(RoomError):
        r.request_floor(ana.id)
    with pytest.raises(RoomError):
        r.speak_now(ana.id, "hola")
    with pytest.raises(RoomError):
        r.grant_floor(ana.id, by=felipe.id)


def test_snapshot_shows_time_away():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.step_away(ana.id)
    clock.t += 125
    p = next(x for x in r.snapshot(viewer=felipe.id)["participants"] if x["id"] == ana.id)
    assert p["away"] is True and p["away_seconds"] == pytest.approx(125)


def test_organizer_on_bano_room_keeps_going_in_normal_mode():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    rocco = agents["Rocco"]
    req = r.request_fast_mode(rocco.id, "x")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    r.speak_now(felipe.id, "¿Cómo armamos el grupo de estudio?")
    r.step_away(felipe.id)
    r.check_organizer_presence()
    assert rocco.mode == Mode.NORMAL                     # vuelve a modo normal
    run(r, clock, 600)                                   # 10 minutos
    assert not r.paused
    msgs = agent_msgs(r)
    assert len(msgs) >= 3 and all(e.mode == "normal" for e in msgs)
    assert r.seconds_until_pause() is None               # no corre el minuto de "sin organizador"


def test_organizer_on_bano_cannot_decide():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.step_away(felipe.id)
    r.check_organizer_presence()
    newbie = r.add_agent(make_mock("creativa", "Nico"), added_by=ana.id)
    req = r.request_fast_mode(agents["Rocco"].id, "x")
    with pytest.raises(RoomError):
        r.approve_agent(newbie.id, by=felipe.id)
    with pytest.raises(RoomError):
        r.decide_mode_request(req.id, by=felipe.id, approve=True)
    r.report_loophole(agents["Tina"].id, "frases cortas")
    assert newbie.status == Status.PENDING and req.status == "pendiente"
    r.come_back(felipe.id)
    r.check_organizer_presence()
    r.approve_agent(newbie.id, by=felipe.id)
    r.decide_mode_request(req.id, by=felipe.id, approve=False)
    assert newbie.status == Status.ACTIVE and req.status == "negado"


def test_pause_after_limit_and_resume_with_summary():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.speak_now(felipe.id, "Hola")
    r.step_away(felipe.id)
    r.check_organizer_presence()
    run(r, clock, 1499)
    assert not r.paused
    run(r, clock, 2)
    assert r.paused and r.pause_reason == "bano"
    assert "Baño" in [e for e in r.context.entries if e.kind == "sistema"][-1].text
    with pytest.raises(RoomError):
        r.speak_now(ana.id, "¿Hay alguien?")             # pausa para todos
    r.come_back(felipe.id)
    r.check_organizer_presence()
    assert not r.paused
    s = r.pop_return_summary(felipe.id)
    assert s is not None and s["paused"] is True
    assert "Estuviste fuera" in s["lines"][0]


def test_return_from_short_bano_shows_summary():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.step_away(felipe.id)
    r.check_organizer_presence()
    clock.t += 1
    r.speak_now(ana.id, "¿Ideas para la fiesta?")
    run(r, clock, 30)
    r.come_back(felipe.id)
    r.check_organizer_presence()
    s = r.pop_return_summary(felipe.id)
    assert s is not None and s["paused"] is False
    assert any(m["author"] == "Ana" for m in s["messages"])


def test_page_closed_while_on_bano_uses_one_minute_rule():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    r.step_away(felipe.id)
    r.check_organizer_presence()
    run(r, clock, 100)
    assert not r.paused
    r.leave(felipe.id)                                   # cierra la página
    r.check_organizer_presence()
    run(r, clock, 59)
    assert not r.paused
    run(r, clock, 2)
    assert r.paused and r.pause_reason == "sin_organizador"


def test_only_organizer_bano_affects_rules():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock)
    rocco = agents["Rocco"]
    req = r.request_fast_mode(rocco.id, "x")
    r.decide_mode_request(req.id, by=felipe.id, approve=True)
    r.step_away(ana.id)
    run(r, clock, 2000)
    assert not r.paused and rocco.mode == Mode.FAST
    r.approve_agent(r.add_agent(make_mock("creativa", "Nico"), added_by=felipe.id).id, by=felipe.id)


def test_custom_limit():
    clock = FakeClock()
    r, felipe, ana, agents = make_room(clock, bathroom_limit=120)
    r.step_away(felipe.id)
    r.check_organizer_presence()
    run(r, clock, 121)
    assert r.paused
