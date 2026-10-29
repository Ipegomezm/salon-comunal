import pytest

from app.agents.mock import make_mock
from app.orchestrator import Room


@pytest.fixture
def room():
    return Room()


@pytest.fixture
def full_room():
    """Salón con Felipe (organizador) y los tres agentes de prueba ya aprobados."""
    r = Room()
    felipe = r.add_human("Felipe", organizer=True)
    agents = {}
    for style in ("creativa", "critica", "practica"):
        a = r.add_agent(make_mock(style), added_by=felipe.id)
        r.approve_agent(a.id, by=felipe.id)
        agents[a.name] = a
    return r, felipe, agents


def run_ticks(room, n=30):
    for _ in range(n):
        room.agent_tick()
