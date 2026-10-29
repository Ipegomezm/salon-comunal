import pytest

from app.agents.mock import make_mock
from app.orchestrator import RoomError, Status


def test_new_agent_is_pending(room):
    felipe = room.add_human("Felipe", organizer=True)
    a = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    assert a.status == Status.PENDING


def test_pending_agent_cannot_speak_or_read(room):
    felipe = room.add_human("Felipe", organizer=True)
    a = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    with pytest.raises(RoomError):
        room.request_floor(a.id)
    with pytest.raises(RoomError):
        room.say(a.id, "hola")
    with pytest.raises(RoomError):
        room.context_for(a.id)
    with pytest.raises(RoomError):
        room.view_for(a.id)


def test_pending_agent_is_ignored_by_tick(room):
    felipe = room.add_human("Felipe", organizer=True)
    a = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    room.speak_now(felipe.id, "Tengo una idea")
    for _ in range(10):
        room.agent_tick()
    assert not any(e.author_id == a.id for e in room.context.entries)


def test_agents_cannot_approve(room):
    felipe = room.add_human("Felipe", organizer=True)
    a1 = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    room.approve_agent(a1.id, by=felipe.id)
    a2 = room.add_agent(make_mock("critica"), added_by=felipe.id)
    with pytest.raises(RoomError):
        room.approve_agent(a2.id, by=a1.id)  # un agente no aprueba a otro
    assert a2.status == Status.PENDING
    room.approve_agent(a2.id, by=felipe.id)
    assert a2.status == Status.ACTIVE
    room.context_for(a2.id)  # ya puede leer


def test_reject_agent(room):
    felipe = room.add_human("Felipe", organizer=True)
    a = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    room.reject_agent(a.id, by=felipe.id)
    assert a.status == Status.REJECTED
    with pytest.raises(RoomError):
        room.request_floor(a.id)
    with pytest.raises(RoomError):
        room.approve_agent(a.id, by=felipe.id)


def test_agents_cannot_add_agents(room):
    felipe = room.add_human("Felipe", organizer=True)
    a = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    room.approve_agent(a.id, by=felipe.id)
    with pytest.raises(RoomError):
        room.add_agent(make_mock("critica"), added_by=a.id)


def test_humans_join_directly(room):
    p = room.add_human("Ana")
    assert p.status == Status.ACTIVE
    room.request_floor(p.id)
    assert room.turns.speaker == p.id


def test_non_organizer_cannot_approve_or_reject(room):
    felipe = room.add_human("Felipe", organizer=True)
    ana = room.add_human("Ana")
    a = room.add_agent(make_mock("creativa"), added_by=felipe.id)
    with pytest.raises(RoomError):
        room.approve_agent(a.id, by=ana.id)
    with pytest.raises(RoomError):
        room.reject_agent(a.id, by=ana.id)
    assert a.status == Status.PENDING
