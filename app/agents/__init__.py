"""Agentes: la interfaz común (adaptador) y agentes de prueba."""
from .base import AgentAdapter, AgentReply, AgentView, TextOnlyVoice, VoiceBackend
from .mock import MockAgent, make_mock

__all__ = ["AgentAdapter", "AgentReply", "AgentView", "TextOnlyVoice", "VoiceBackend", "MockAgent", "make_mock"]
