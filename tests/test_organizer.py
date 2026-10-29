import pytest

from app.agents.mock import make_mock
from app.orchestrator import RoomError, Status


@pytest.fixture
def setup(room):
    felipe = room.add_human("Felipe", organizer=True)
    ana = room.add_human("Ana")
    lumi = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    room.approve_agent(lumi.id, by=felipe.id)
    return room, felipe, ana, lumi


def test_typed_name_does_not_make_organizer(room):
    p = room.add_human("Felipe")
    assert p.organizer is False


def test_organizer_grants_role_to_person(setup):
    r, felipe, ana, lumi = setup
    r.grant_organizer(ana.id, by=felipe.id)
    assert ana.organizer
    pending = r.add_agent(make_mock("critica"), added_by=ana.id)
    r.approve_agent(pending.id, by=ana.id)
    assert pending.status == Status.ACTIVE


def test_organizer_can_grant_role_to_agent(setup):
    r, felipe, ana, lumi = setup
    r.grant_organizer(lumi.id, by=felipe.id)
    assert lumi.organizer


def test_non_organizer_cannot_grant_or_revoke(setup):
    r, felipe, ana, lumi = setup
    with pytest.raises(RoomError):
        r.grant_organizer(ana.id, by=ana.id)
    with pytest.raises(RoomError):
        r.revoke_organizer(felipe.id, by=ana.id)
    assert not ana.organizer and felipe.organizer


def test_agent_cannot_grant_itself_or_others(setup):
    r, felipe, ana, lumi = setup
    with pytest.raises(RoomError):
        r.grant_organizer(lumi.id, by=lumi.id)
    with pytest.raises(RoomError):
        r.grant_organizer(ana.id, by=lumi.id)
    # aun siendo organizador, un agente no da ni quita el rol
    r.grant_organizer(lumi.id, by=felipe.id)
    rocco = r.add_agent(make_mock("critica"), added_by=felipe.id)
    r.approve_agent(rocco.id, by=felipe.id)
    with pytest.raises(RoomError):
        r.grant_organizer(rocco.id, by=lumi.id)
    with pytest.raises(RoomError):
        r.grant_organizer(ana.id, by=lumi.id)
    with pytest.raises(RoomError):
        r.revoke_organizer(felipe.id, by=lumi.id)
    assert not rocco.organizer and not ana.organizer and felipe.organizer


def test_cannot_grant_to_pending_agent(setup):
    r, felipe, ana, lumi = setup
    pending = r.add_agent(make_mock("critica"), added_by=felipe.id)
    with pytest.raises(RoomError):
        r.grant_organizer(pending.id, by=felipe.id)


def test_revoke_role(setup):
    r, felipe, ana, lumi = setup
    r.grant_organizer(ana.id, by=felipe.id)
    r.revoke_organizer(ana.id, by=felipe.id)
    assert not ana.organizer
    with pytest.raises(RoomError):
        r.revoke_organizer(ana.id, by=felipe.id)  # ya no lo es


def test_last_organizer_cannot_be_removed(setup):
    r, felipe, ana, lumi = setup
    with pytest.raises(RoomError):
        r.revoke_organizer(felipe.id, by=felipe.id)
    assert felipe.organizer
    r.grant_organizer(ana.id, by=felipe.id)
    r.revoke_organizer(felipe.id, by=felipe.id)  # ahora sí, Ana sigue
    assert not felipe.organizer and ana.organizer
    with pytest.raises(RoomError):
        r.revoke_organizer(ana.id, by=ana.id)


def test_role_changes_are_in_transcript(setup):
    r, felipe, ana, lumi = setup
    r.grant_organizer(ana.id, by=felipe.id)
    assert "le dio el rol de organizador a Ana" in r.context.entries[-1].text


def test_mode_requests_only_shown_to_organizers(setup):
    r, felipe, ana, lumi = setup
    r.request_fast_mode(lumi.id, "x")
    assert len(r.snapshot(viewer=felipe.id)["mode_requests"]) == 1
    assert r.snapshot(viewer=ana.id)["mode_requests"] == []
    assert r.snapshot(viewer=felipe.id)["you_are_organizer"] is True
    assert r.snapshot(viewer=ana.id)["you_are_organizer"] is False
