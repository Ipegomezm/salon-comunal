import pytest

from app.agents.mock import make_mock
from app.orchestrator import RoomError
from app.orchestrator.room import DEFAULT_ORGANIZER_GRACE_SECONDS, Room


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def setup(clock):
    r = Room(clock=clock)
    felipe = r.add_human("Felipe", organizer=True)
    ana = r.add_human("Ana")
    lumi = r.add_agent(make_mock("creativa"), added_by=felipe.id)
    r.approve_agent(lumi.id, by=felipe.id)
    r.check_organizer_presence()
    return r, felipe, ana, lumi


def test_default_is_one_minute():
    assert DEFAULT_ORGANIZER_GRACE_SECONDS == 60
    assert Room().organizer_grace == 60


def test_no_pause_while_organizer_present(setup, clock):
    r, felipe, ana, lumi = setup
    clock.t = 1000
    r.check_organizer_presence()
    assert not r.paused and r.seconds_until_pause() is None


def test_pauses_after_60s_without_organizer(setup, clock):
    r, felipe, ana, lumi = setup
    r.leave(felipe.id)
    r.check_organizer_presence()
    clock.t = 59
    r.check_organizer_presence()
    assert not r.paused and r.seconds_until_pause() == pytest.approx(1)
    clock.t = 60
    r.check_organizer_presence()
    assert r.paused
    assert "pausa" in r.context.entries[-1].text


def test_paused_room_blocks_humans_and_agents(setup, clock):
    r, felipe, ana, lumi = setup
    r.leave(felipe.id)
    r.check_organizer_presence()
    clock.t = 61
    r.check_organizer_presence()
    with pytest.raises(RoomError):
        r.speak_now(ana.id, "hola")
    with pytest.raises(RoomError):
        r.request_floor(ana.id)
    with pytest.raises(RoomError):
        r.request_floor(lumi.id)
    with pytest.raises(RoomError):
        r.add_agent(make_mock("critica"))
    before = len(r.context.entries)
    assert r.agent_tick() is False
    assert len(r.context.entries) == before


def test_reload_within_grace_does_not_pause(setup, clock):
    r, felipe, ana, lumi = setup
    r.leave(felipe.id)          # recarga la página / se cae la conexión
    r.check_organizer_presence()
    clock.t = 45
    felipe2 = r.add_human("Felipe", organizer=True)  # vuelve con el link secreto
    r.check_organizer_presence()
    clock.t = 200
    r.check_organizer_presence()
    assert not r.paused
    r.speak_now(felipe2.id, "Ya volví")


def test_resumes_when_organizer_returns(setup, clock):
    r, felipe, ana, lumi = setup
    r.leave(felipe.id)
    r.check_organizer_presence()
    clock.t = 70
    r.check_organizer_presence()
    assert r.paused
    r.add_human("Felipe", organizer=True)
    r.check_organizer_presence()
    assert not r.paused
    r.speak_now(ana.id, "Seguimos")


def test_agent_organizer_does_not_count_as_present(setup, clock):
    r, felipe, ana, lumi = setup
    r.grant_organizer(lumi.id, by=felipe.id)
    r.leave(felipe.id)
    r.check_organizer_presence()
    clock.t = 60
    r.check_organizer_presence()
    assert r.paused


def test_room_without_any_organizer_pauses_after_start(clock):
    r = Room(clock=clock)
    r.add_human("Ana")
    clock.t = 60
    r.check_organizer_presence()
    assert r.paused


def test_custom_grace(clock):
    r = Room(organizer_grace=5, clock=clock)
    clock.t = 5
    r.check_organizer_presence()
    assert r.paused


def test_snapshot_shows_pause_state(setup, clock):
    r, felipe, ana, lumi = setup
    assert r.snapshot(viewer=ana.id)["paused"] is False
    r.leave(felipe.id)
    r.check_organizer_presence()
    clock.t = 30
    snap = r.snapshot(viewer=ana.id)
    assert snap["seconds_until_pause"] == pytest.approx(30)
    clock.t = 60
    r.check_organizer_presence()
    assert r.snapshot(viewer=ana.id)["paused"] is True
