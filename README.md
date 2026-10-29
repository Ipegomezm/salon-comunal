# Salón Comunal

**Varios agentes de voz conversando juntos en una misma llamada.**

## Qué es

Salón Comunal es un proyecto para conectar **varios agentes de voz en una sola llamada compartida**. Funciona como una conversación en grupo: cada agente tiene **su propia voz** y personalidad, y todos participan junto con una o más personas, como en un salón comunal donde la gente se reúne a hablar.

## Cómo funciona

Para que la conversación fluya hace falta un **orquestador** en el centro, que se encarga de tres cosas:

1. **Enrutar el audio:** recibe lo que se dice en la llamada y lo reparte entre los agentes, y devuelve a la llamada la voz de cada uno.
2. **Manejar los turnos de palabra:** decide quién habla y cuándo, para que los agentes no se pisen ni hablen todos a la vez, y maneja las interrupciones.
3. **Mantener un contexto compartido:** guarda lo que se ha dicho para que cada participante sepa en qué va la conversación y responda con sentido.

Cada agente puede usar una API de voz distinta; el orquestador los une en una misma llamada.

## Agentes externos por link

Además de los agentes de voz integrados, Salón Comunal permitirá **invitar a un agente externo con solo darle un link**: la URL del endpoint o servicio de otro agente. El orquestador se conecta a ese link, suma al agente a la llamada con su propia voz y lo incluye en los turnos de palabra y en el contexto compartido, igual que a los demás. Así cualquiera puede traer su propio agente al salón.

## Ejemplos de uso

- **Grupo de estudio con un tutor de IA:** varios estudiantes y un tutor que explica, pregunta y corrige.
- **Llamada familiar con varios asistentes:** cada asistente ayuda con algo distinto (agenda, recetas, tareas) en la misma conversación.
- **Lluvia de ideas:** cada voz aporta una perspectiva diferente (creativa, crítica, práctica) sobre un mismo problema.

## Estado

Todavía no hay código. Este README es el punto de partida del proyecto.
