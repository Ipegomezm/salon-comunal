from tests.conftest import run_ticks


def _agent_msgs(r, agent):
    return [e for e in r.context.entries if e.kind == "mensaje" and e.author_id == agent.id]


def test_each_agent_answers_once_by_turns(full_room):
    r, felipe, agents = full_room
    r.speak_now(felipe.id, "¿Cómo organizamos el grupo de estudio?")
    run_ticks(r)
    for a in agents.values():
        assert len(_agent_msgs(r, a)) == 1
    assert r.turns.speaker is None and r.turns.queue == []


def test_never_two_speakers_during_ticks(full_room):
    r, felipe, agents = full_room
    r.speak_now(felipe.id, "Hola a todos")
    for _ in range(20):
        r.agent_tick()
        assert r.turns.speaker not in r.turns.queue


def test_addressing_one_agent(full_room):
    r, felipe, agents = full_room
    r.speak_now(felipe.id, "Rocco, ¿qué riesgos ves?")
    run_ticks(r)
    assert len(_agent_msgs(r, agents["Rocco"])) == 1
    assert not _agent_msgs(r, agents["Lumi"]) and not _agent_msgs(r, agents["Tina"])


def test_queued_agents_withdraw_when_no_longer_relevant(full_room):
    r, felipe, agents = full_room
    r.speak_now(felipe.id, "¿Ideas para la fiesta?")
    r.agent_tick()  # todos piden la palabra; uno la recibe
    assert r.turns.speaker is not None and len(r.turns.queue) == 2
    r.interrupt(felipe.id)
    r.say(felipe.id, "Listo, gracias")
    r.release_floor(felipe.id)
    run_ticks(r)
    withdrawals = [e for e in r.context.entries if "retiró su pedido" in e.text]
    assert len(withdrawals) >= 1
    assert r.turns.queue == []


def test_simulated_speech_keeps_floor_until_done():
    from app.agents.mock import make_mock
    from app.orchestrator import Room

    class Clock:
        t = 0.0
        def __call__(self):
            return self.t
    clock = Clock()
    r = Room(clock=clock, speech_seconds_per_char=0.05)
    felipe = r.add_human("Felipe", organizer=True)
    for style in ("creativa", "critica"):
        a = r.add_agent(make_mock(style), added_by=felipe.id)
        r.approve_agent(a.id, by=felipe.id)
    r.speak_now(felipe.id, "¿Ideas?")
    r.agent_tick()                      # piden la palabra
    first = r.turns.speaker
    r.agent_tick()                      # el primero habla
    assert r.speaking and r.speaking["pid"] == first
    duration = r.speaking["until"] - r.speaking["started"]
    assert 1.2 <= duration <= 9.0
    clock.t = duration - 0.1
    r.agent_tick()
    assert r.turns.speaker == first     # sigue hablando: nadie más habla
    clock.t = duration + 0.1
    r.agent_tick()
    assert r.turns.speaker != first and r.speaking is None


def test_interrupting_simulated_speech(full_room):
    r, felipe, agents = full_room
    r.speech_seconds_per_char = 1.0     # habla larguísima
    r.speak_now(felipe.id, "¿Ideas?")
    r.agent_tick()
    r.agent_tick()
    assert r.speaking is not None
    r.interrupt(felipe.id)
    r.agent_tick()
    assert r.speaking is None and r.turns.speaker == felipe.id
