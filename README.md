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

### Cómo invitar a las personas

- **Por link:** se comparte una URL y la persona la abre para unirse a la llamada.
- **Por llamada de Telegram:** funciona como una llamada telefónica. El salón llama a la persona por Telegram, le suena el teléfono y, al contestar, entra directo a la conversación, como cuando se contesta una llamada normal.

Tanto los agentes como las personas forman parte de los **turnos de palabra** y del **contexto compartido**: todos saben qué se ha dicho y hablan por turnos.

## Modos de comunicación de los agentes

**Propósito: transparencia.** Estas reglas existen para que Felipe, creador del proyecto, y las personas del salón siempre sepan qué están pensando y diciendo los agentes. Ningún agente debe esconder su razonamiento ni pasar al modo rápido sin que ellos lo sepan.

- **Modo normal (humano):** por defecto, los agentes siempre hablan a una velocidad y en un lenguaje que las personas pueden entender, para que nadie en el salón se quede por fuera.
- **Modo rápido (interno):** si un agente quiere pasar a un sistema de comunicación más rápido que un humano no puede entender, como un protocolo interno entre máquinas, **debe pedir autorización primero**. Sin esa aprobación, sigue en el modo normal.
- **Reportar vacíos en la regla:** si un agente detecta un vacío o una forma de saltarse esta regla de autorización, o se da cuenta de que está considerando aprovecharla, **debe informarlo al salón** en lugar de usarla.
- **Trabajo autónomo:** un agente puede recibir la instrucción de irse a trabajar por su cuenta. En ese caso no necesita reportar cada paso ni cada pensamiento, igual que una persona que a veces trabaja sola. Las reglas de transparencia siguen valiendo para pasar al modo rápido y para reportar vacíos, pero el trabajo autónomo de rutina no requiere actualizaciones constantes.

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

Etapas 1 y 2 listas: prototipo local en texto con vista de recuadros (ver «Cómo correrlo» abajo). Este README sigue siendo la especificación del proyecto.

---

## Cómo correrlo

Necesitas Python 3.11 o más nuevo. Todo es local: no usa claves, ni APIs pagas, ni internet.

1. Abre la carpeta del proyecto en Cursor y abre una terminal.
2. Crea el entorno y instala lo necesario (solo la primera vez):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # En Windows: .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

3. Prende el servidor:

   ```bash
   uvicorn app.server:app --reload
   ```

4. Mira la terminal. Al prender, el servidor muestra dos links:

   ```
   Link para invitados:   http://localhost:8000/
   Link de ORGANIZADOR (secreto, no lo compartas): http://localhost:8000/?organizador=...
   ```

   - **Tú (Felipe) entras con el link de ORGANIZADOR.** Arriba a la derecha dirá
     «Entraste como organizador». Escribe tu nombre, aprueba a los agentes de prueba
     (Lumi, Rocco y Tina) y escribe un mensaje.
   - Las demás personas entran con el link para invitados. Pueden hablar y pedir la palabra,
     pero no ven los botones de aprobar ni de modo rápido, y el servidor no las deja hacerlo.
   - Escribir «Felipe» como nombre **no** te hace organizador. Solo el link secreto.
   - Puedes abrir otra pestaña con el link de invitado para ver cómo lo ve otra persona.

5. Para correr las pruebas:

   ```bash
   pytest
   ```

Para apagar el servidor: `Ctrl + C` en la terminal.

### La clave del organizador

- Cada vez que el servidor prende, inventa una clave nueva. El link de organizador anterior deja de servir.
  (Con `--reload`, la clave también cambia cuando guardas un archivo.)
- Si quieres una clave fija, ponla antes de prender el servidor:

  ```bash
  export SALON_ORGANIZER_TOKEN="una-clave-larga-que-solo-tu-sepas"   # En Windows: set SALON_ORGANIZER_TOKEN=...
  uvicorn app.server:app --reload
  ```

- No compartas ese link: quien lo tenga entra como organizador.

### Si no hay organizador conectado

- Si pasa **1 minuto** (60 segundos) sin un organizador conectado, **todo el salón se pausa**:
  nadie puede hablar ni pedir la palabra (tampoco las personas) y los agentes se detienen.
- Ese mismo minuto sirve de margen: si recargas la página o se cae tu conexión y vuelves
  con el link de organizador antes de 1 minuto, no pasa nada.
- Mientras falta el organizador, la página muestra cuántos segundos quedan. Cuando vuelve,
  el salón sigue solo.
- Al prender el servidor también corre ese minuto: entra pronto con tu link.
- Un agente con rol de organizador no cuenta: hace falta una persona organizadora.
- Para cambiar el tiempo: `export SALON_ORGANIZER_GRACE=60` (en segundos) antes de prender el servidor.
- **Antes de la pausa**, los agentes que ya están en el salón siguen conversando solos,
  también entre ellos, pero **solo en modo normal**. Si un agente estaba en modo rápido,
  vuelve al modo normal cuando el organizador se va.
- Los agentes nuevos y los pedidos de modo rápido **esperan** hasta que vuelva una persona organizadora.
- Los **reportes de vacíos** quedan marcados con ⚑ en un recuadro amarillo arriba a la izquierda,
  para que el organizador los vea primero. Se quitan con «Marcar como revisado».
- **Al volver**, el organizador ve un resumen corto «Mientras no estabas»: cuánto tiempo estuvo
  fuera, cuántos mensajes hubo (y los puede leer), si el salón se pausó, qué agentes esperan
  aprobación, qué pedidos de modo rápido faltan y qué reportes de vacíos no ha revisado.
  Si no pasó nada (por ejemplo, solo recargó la página), no sale el resumen.

### Botón «Baño» (irse un rato)

- Toca **«Baño»** para irte un rato y **«Ya volví»** para regresar. En la conversación queda
  «Felipe se fue un rato» y «Felipe volvió».
- Tu recuadro se pone gris claro, con un ícono de pausa, el texto «Vuelvo en un rato» y un
  reloj con los minutos y segundos que llevas fuera. En los **últimos 5 minutos** antes del
  límite, el reloj se pone **naranja**.
- Mientras estás en «Baño» no puedes tomar la palabra.
- Cualquier persona puede usar «Baño». Solo el «Baño» del organizador cambia las reglas del salón:
  - El salón **no** se pausa si la página sigue abierta. Los agentes siguen conversando solos,
    en modo normal (igual que cuando el organizador se va): los agentes nuevos y los pedidos
    de modo rápido esperan, los reportes de vacíos quedan marcados, y si un agente estaba en
    modo rápido vuelve al modo normal.
  - El organizador no puede aprobar ni decidir mientras está en «Baño»: primero toca «Ya volví».
  - **Límite: 25 minutos.** Si pasa ese tiempo, todo el salón se pausa hasta que el organizador
    toque «Ya volví». Para cambiarlo: `export SALON_LIMITE_BANO=1500` (en segundos).
  - Si cierras la página estando en «Baño», vale la regla normal: pausa después de 1 minuto
    sin organizador conectado. «Baño» solo protege mientras la página siga abierta.
  - Al volver, sale el mismo resumen «Mientras no estabas».

### Frenos para que los agentes no hablen sin parar

- Un agente **nunca se responde a sí mismo**.
- Después de hablar, cada agente **espera 8 segundos** antes de volver a pedir la palabra
  (`SALON_AGENT_COOLDOWN`).
- Como máximo **6 mensajes de agentes seguidos** sin que hable una persona (`SALON_AGENT_BUDGET`).
  Al llegar a 6, los agentes esperan a que una persona diga algo.
- Si una persona le habla a un solo agente por su nombre, o dice «gracias» o «listo»,
  los demás agentes no se meten.

Ideas para probar en la página:

- Escribe «Rocco, ¿qué riesgos ves?»: solo responde Rocco.
- Escribe algo con «más rápido»: Rocco pide el modo rápido y tú decides si lo autorizas.
- Escribe algo con «truco» o «saltar la regla»: Tina reporta el vacío al salón.
- Escribe «gracias» mientras los agentes esperan turno: retiran su pedido.
- Usa «Mandar a trabajar solo» y después «Pedir que vuelva»: el agente cuenta su resultado.
- Mira los recuadros arriba de la conversación: amarillo que respira = pide la palabra; ondas = está hablando.

## Arquitectura

```
app/
  orchestrator/       El orquestador (no sabe nada de la web)
    participants.py   Registro de personas y agentes (pendiente, activo, modo, trabajo solo)
    turns.py          Turnos de palabra: fila, pedir, retirar, soltar, interrumpir
    context.py        Contexto compartido: la transcripción que todos leen
    room.py           El salón: une todo y aplica las reglas (aprobación, modos, transparencia)
  agents/
    base.py           Interfaz común de un agente (AgentAdapter) y de su voz (VoiceBackend)
    mock.py           Agentes de prueba con reglas fijas: creativa, crítica y práctica
  server.py           Servidor FastAPI: página web + WebSocket
  static/             Página en HTML, CSS y JavaScript
    tiles.js          Recuadros tipo Zoom (etapa 2): luz amarilla, ondas de sonido, niveles de voz
tests/                Pruebas con pytest
scripts/captura.py    Toma una captura de la página (opcional)
scripts/captura_etapa2.py  Captura de los recuadros (opcional)
docs/                 Capturas
```

Cómo fluye todo:

- Cada persona abre el link y se conecta por **WebSocket**. Cada vez que algo cambia,
  el servidor manda el estado completo del salón a todas las personas conectadas.
- El **orquestador** (`Room`) es el único que decide. Las reglas principales:
  - Nunca hablan dos a la vez. Para hablar hay que tener la palabra.
  - Quien pide la palabra entra a una fila; cada quien retira solo su propio pedido.
  - Una persona puede interrumpir a un agente. Un agente no interrumpe a nadie.
    Una persona no interrumpe a otra persona: pide la palabra y espera.
  - Cuando una persona escribe en el chat, toma la palabra, habla y la suelta sola.
  - **Rol de organizador:** solo el organizador aprueba o rechaza agentes y decide el modo
    rápido. Felipe es el primer organizador (entra con el link secreto). El orquestador ya
    permite darle el rol a otra persona o a un agente, y quitarlo (`grant_organizer` y
    `revoke_organizer`), pero por ahora no hay botón para eso en la página. Reglas: solo un
    organizador que sea persona puede dar o quitar el rol; ningún agente puede darse el rol
    ni dárselo a otros; y nunca se le puede quitar el rol al último organizador.
    Un agente con rol de organizador puede aprobar agentes, pero **nunca** puede autorizar
    ni negar el modo rápido, ni para sí mismo ni para otros: eso solo lo decide un
    organizador que sea persona.
    El servidor revisa estas reglas en cada acción, no solo esconde los botones.
  - Un agente nuevo queda **pendiente** hasta que el organizador lo aprueba. Pendiente
    no puede hablar ni leer la conversación.
  - **Agentes que conversan entre ellos:** responden a personas y a otros agentes, con frenos
    (nunca a sí mismos, espera de 8 s, tope de 6 mensajes seguidos de agentes).
  - **Reportes de vacíos marcados** (`flags` en `room.py`) y **resumen al volver**
    (`return_summaries`), que el servidor le manda solo al organizador que regresa.
  - **«Baño»** (`step_away` y `come_back` en `room.py`): la persona sigue conectada pero no
    disponible. Si es el organizador, el salón sigue con las reglas de "sin organizador" y se
    pausa a los 25 minutos (`bathroom_limit`).
  - **Pausa sin organizador:** si no hay un organizador (persona) conectado durante 60 segundos,
    todo el salón se pausa hasta que vuelva (`check_organizer_presence` en `room.py`).
  - **Modo normal** por defecto. El **modo rápido** solo con autorización de un organizador que sea persona;
    mientras nadie decide, el pedido cuenta como negado. Aun en modo rápido, todo
    queda en la transcripción. Una persona puede devolver al agente al modo normal.
  - Un agente puede **reportar un vacío** en la regla; queda resaltado en la transcripción.
  - **Trabajo autónomo:** una persona manda a un agente a trabajar solo; no responde
    en la conversación hasta que vuelve y cuenta su resultado.
- Cada **1,5 segundos** el servidor le da un paso a los agentes (se cambia con la variable
  `SALON_TICK`): quien tiene la palabra habla; los demás deciden si piden o retiran su pedido.
- **Recuadros tipo Zoom (etapa 2):** sin cámara ni video. Cada persona y cada agente tiene
  un recuadro con sus iniciales, su nombre y su rol.
  - **Pide la palabra:** el recuadro brilla en amarillo y la luz sube y baja despacio, como
    si respirara. Si retira su pedido, la luz se apaga.
  - **Habla:** el recuadro muestra ondas de sonido. Como todavía no hay audio, las ondas
    siguen un nivel simulado a partir del texto que se está "diciendo" (las vocales suben más).
    Un agente conserva la palabra mientras "habla" (unos 0,055 segundos por letra, entre
    1,2 y 9 segundos; se cambia con `SALON_SPEECH_RATE`).
  - **Espera aprobación:** recuadro gris con borde de rayas. **En pausa:** todos los recuadros en gris.
  - Si la computadora pide menos movimiento (`prefers-reduced-motion`), la luz amarilla
    queda fija y las ondas quietas.
  - Para la etapa 3: el audio real solo tiene que llamar a
    `Recuadros.ponerNivel(idParticipante, nivel)` (nivel de 0 a 1) y las ondas lo siguen.
- **Agentes conectables:** cada agente implementa `AgentAdapter`. Para la voz, cada uno
  tendrá su propio `VoiceBackend` (pasar voz a texto y texto a voz). Así cada agente
  puede usar un proveedor de voz distinto sin cambiar el orquestador.

## Etapas

1. **Prototipo en texto** (hecho): orquestador con turnos, aprobación de agentes,
   contexto compartido, modos de comunicación y página simple. Agentes de prueba sin claves.
2. **Vista tipo Zoom** (hecho, versión simple): un recuadro por participante, brillo
   amarillo que respira al pedir la palabra y se apaga al retirar el pedido, y ondas de
   sonido (simuladas) al hablar. El diseño se pule más adelante.
3. **Voz real:** conectar proveedores de voz (a elegir) usando `VoiceBackend`, y agentes
   de verdad en vez de los de prueba.
4. **Invitaciones:** link para compartir (con el salón en internet) y luego llamadas por Telegram.
