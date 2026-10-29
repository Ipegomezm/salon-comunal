# multi-voice-call

**Llamadas de voz con varios agentes a la vez.**

## La idea

Hoy una llamada con un asistente de voz es de dos: una persona y un agente. Este proyecto busca ir más allá: un **orquestador** que conecta varias APIs de voz para que **tres o más agentes** (y una o más personas) conversen juntos en la misma llamada, como una conferencia telefónica normal.

## Cómo funcionaría

- **Orquestador central:** recibe el audio de la llamada y lo reparte a cada agente.
- **Varios proveedores de voz:** cada agente puede usar una API distinta (con su propia voz y personalidad).
- **Turnos de palabra:** el orquestador decide quién habla, evita que se pisen y maneja interrupciones.
- **Contexto compartido:** todos los agentes "escuchan" la conversación completa para responder con sentido.

## Ejemplos de uso

- Un experto en finanzas, uno en tecnología y un moderador hablando contigo al mismo tiempo.
- Practicar una reunión o negociación con varios participantes.
- Una mesa redonda de agentes especializados para resolver un problema.

## Estado

Idea inicial. Todavía no hay código.
