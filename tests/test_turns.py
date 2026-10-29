import pytest

from app.orchestrator import FloorError, RoomError, TurnManager


def test_first_request_gets_floor_others_queue():
    t = TurnManager()
    assert t.request("a") is True
    assert t.request("b") is False
    assert t.request("c") is False
    assert t.speaker == "a" and t.queue == ["b", "c"]


def test_release_passes_to_next_in_order():
    t = TurnManager()
    for p in "abc":
        t.request(p)
    assert t.release("a") == "b"
    assert t.release("b") == "c"
    assert t.release("c") is None
    assert t.speaker is None


def test_never_two_speakers_and_no_duplicates():
    t = TurnManager()
    t.request("a")
    t.request("b")
    t.request("b")
    assert t.queue == ["b"]
    with pytest.raises(FloorError):
        t.request("a")  # ya tiene la palabra
    with pytest.raises(FloorError):
        t.grant("b")    # alguien ya la tiene


def test_withdraw_own_request():
    t = TurnManager()
    t.request("a")
    t.request("b")
    t.withdraw("b")
    assert t.queue == []
    with pytest.raises(FloorError):
        t.withdraw("b")


def test_only_speaker_can_release():
    t = TurnManager()
    t.request("a")
    t.request("b")
    with pytest.raises(FloorError):
        t.release("b")


def test_interrupt_replaces_speaker():
    t = TurnManager()
    t.request("agent")
    t.request("x")
    assert t.interrupt("human") == "agent"
    assert t.speaker == "human" and t.queue == ["x"]


def test_room_speak_requires_floor(full_room):
    r, felipe, agents = full_room
    lumi = agents["Lumi"].id
    with pytest.raises(RoomError):
        r.say(lumi, "hola")
    r.request_floor(lumi)
    r.say(lumi, "hola")
    assert r.context.entries[-1].text == "hola"


def test_room_withdraw_only_own(full_room):
    r, felipe, agents = full_room
    lumi, rocco, tina = (agents[n].id for n in ("Lumi", "Rocco", "Tina"))
    r.request_floor(lumi)   # recibe la palabra
    r.request_floor(rocco)  # en fila
    with pytest.raises(RoomError):
        r.withdraw_floor(tina)  # Tina no puede retirar el pedido de Rocco (ni tiene pedido)
    assert rocco in r.turns.queue
    r.withdraw_floor(rocco)
    assert rocco not in r.turns.queue
    assert "retiró su pedido" in r.context.entries[-1].text


def test_human_can_interrupt_agent_but_not_human(full_room):
    r, felipe, agents = full_room
    ana = r.add_human("Ana")
    lumi = agents["Lumi"].id
    r.request_floor(lumi)
    r.interrupt(felipe.id)
    assert r.turns.speaker == felipe.id
    with pytest.raises(RoomError):
        r.interrupt(ana.id)  # no se interrumpe a una persona
    with pytest.raises(RoomError):
        r.interrupt(lumi)    # un agente no interrumpe


def test_speak_now_waits_for_other_human(full_room):
    r, felipe, agents = full_room
    ana = r.add_human("Ana")
    r.request_floor(ana.id)
    with pytest.raises(RoomError):
        r.speak_now(felipe.id, "hola")
    r.release_floor(ana.id)
    r.speak_now(felipe.id, "hola")
    assert r.turns.speaker is None


def test_leaving_speaker_passes_floor(full_room):
    r, felipe, agents = full_room
    lumi, rocco = agents["Lumi"].id, agents["Rocco"].id
    r.request_floor(lumi)
    r.request_floor(rocco)
    r.leave(lumi)
    assert r.turns.speaker == rocco
