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

## Quién participa en el salón

En Salón Comunal participan dos tipos de miembros:

1. **Agentes de voz:** son agentes integrados al salón. Una persona puede agregar o conectar un agente a la conversación, pero **cada agente necesita aprobación antes de entrar** a la llamada.
2. **Personas externas:** cualquier persona puede participar directamente en el salón comunal uniéndose a la llamada.

Tanto los agentes como las personas forman parte de los **turnos de palabra** y del **contexto compartido**: todos saben qué se ha dicho y hablan por turnos.

## Interfaz de video

Además del audio, Salón Comunal tendrá una vista en pantalla parecida a una videollamada de Zoom:

- **Un recuadro por participante:** cada persona y cada agente tiene su propio recuadro pequeño de video.
- **Pedir la palabra:** cuando alguien quiere hablar, su recuadro se queda **alumbrando en amarillo**, con una luz que sube y baja suavemente, como si respirara, para que todos sepan que está pidiendo turno.
- **Cancelar el pedido:** un agente que pidió la palabra puede **retirar su propio pedido** si decide que lo que iba a decir ya no es relevante; su recuadro deja de alumbrar en amarillo.
- **Quién está hablando:** el recuadro de quien habla en ese momento muestra **ondas de sonido animadas** que siguen el movimiento de su pronunciación, para ver de un vistazo quién tiene la palabra.

## Ejemplos de uso

- **Grupo de estudio con un tutor de IA:** varios estudiantes y un tutor que explica, pregunta y corrige.
- **Llamada familiar con varios asistentes:** cada asistente ayuda con algo distinto (agenda, recetas, tareas) en la misma conversación.
- **Lluvia de ideas:** cada voz aporta una perspectiva diferente (creativa, crítica, práctica) sobre un mismo problema.

## Estado

Todavía no hay código. Este README es el punto de partida del proyecto.
