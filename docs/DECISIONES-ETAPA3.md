# Decisiones para la etapa 3 (voz) y otras pendientes

Hola, Felipe. Esta hoja es para decidir. Frases cortas.

- **Gratis** = no cuesta dinero. No necesita claves.
- **Pago** = necesita una cuenta, una clave y tu **OK**. No hice nada pago.
- Precios leídos el **29 de octubre de 2026**, en dólares (USD). Pueden cambiar. Revisa el link.

La voz tiene 3 partes:

1. **Oír**: pasar tu voz a texto (en inglés: STT).
2. **Hablar**: pasar el texto del agente a voz (en inglés: TTS).
3. **Llevar el audio** entre las personas del salón (WebRTC).

El salón ya está listo para esto: cada agente puede tener **su propia voz**, de un proveedor distinto.

---

## Tabla corta

| Opción | Para qué | Costo | Dónde corre | Notas |
|---|---|---|---|---|
| **Voz del navegador: reconocer** (Web Speech API) | Oír | Gratis | En el navegador | En Chrome, por defecto **manda tu audio a Google**. Desde Chrome 139 se puede pedir que sea **solo en tu computadora** (`processLocally`). [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API/Using_the_Web_Speech_API) |
| **Voz del navegador: hablar** (speechSynthesis) | Hablar | Gratis | En el navegador | Usa las voces de tu computadora. Suenan algo robóticas. Pocas voces en español. |
| **faster-whisper** | Oír | Gratis (licencia MIT) | En el servidor | Muy bueno en español. Necesita una computadora con fuerza; mejor con tarjeta gráfica. [GitHub](https://github.com/SYSTRAN/faster-whisper) |
| **Piper** | Hablar | Gratis (licencia GPL-3) | En el servidor | Rápido, tiene voces en español. Cambió de lugar y de licencia en 2025. [GitHub](https://github.com/OHF-Voice/piper1-gpl) |
| **Kokoro** | Hablar | Gratis (licencia Apache-2) | En el servidor | Voces más naturales. Tiene 3 voces en español. [Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M) |
| **WebRTC** (aiortc o LiveKit propio) | Llevar el audio | Gratis | En el servidor | LiveKit propio es gratis; LiveKit en la nube es pago. [LiveKit](https://github.com/livekit/livekit) · [aiortc](https://github.com/aiortc/aiortc) |
| **Deepgram** ⚠️ pago | Oír y hablar | Oír: ~0,0077 USD/min. Hablar: 0,03 USD por 1.000 letras. Da 200 USD de prueba. | En la nube | [Precios](https://deepgram.com/pricing) |
| **ElevenLabs** ⚠️ pago | Hablar (y oír) | Hablar: 0,04 a 0,08 USD por 1.000 letras. Plan gratis con 10.000 letras al mes. | En la nube | Voces muy naturales. [Precios](https://elevenlabs.io/pricing/api) |
| **OpenAI** ⚠️ pago | Oír, hablar o conversación en vivo | Oír en vivo: 0,017 USD/min. Conversación en vivo: desde 0,05 USD/min. | En la nube | [Precios](https://developers.openai.com/api/docs/pricing) |
| **Google Cloud** ⚠️ pago | Oír y hablar | Oír: 0,016 USD/min. Voces HD: 30 USD por millón de letras. | En la nube | [Oír](https://cloud.google.com/speech-to-text/pricing) · [Hablar](https://cloud.google.com/text-to-speech/pricing) |
| **Azure (Microsoft)** ⚠️ pago | Oír y hablar | Oír en vivo: cerca de 2 USD/hora. | En la nube | [Precios](https://azure.microsoft.com/en-us/pricing/details/speech/) |
| **LiveKit Cloud** ⚠️ pago | Llevar el audio | Plan gratis pequeño. Pago desde 50 USD/mes. | En la nube | [Precios](https://livekit.com/pricing) |

Cuenta rápida: 1.000 letras son más o menos **1 minuto** de voz.

---

## 3 caminos que recomiendo

### Camino A: todo en el navegador (gratis, lo más rápido)

- Oír y hablar con lo que ya trae el navegador.
- **A favor:** no hay que instalar nada. Se puede probar pronto.
- **En contra:** voces robóticas. Funciona mejor en Chrome. Si no usamos «solo en tu computadora», tu voz va a Google.
- **(a) Decidido: solo en tu computadora, nunca a Google.** Si tu navegador no puede hacerlo
  solo en tu computadora, la voz no se usa y sale un aviso en español. Nunca se manda tu audio a internet.

### Camino B: todo en tu computadora (gratis, mejor calidad)

- Oír con **faster-whisper**. Hablar con **Kokoro** o **Piper**. Audio con **WebRTC**.
- **A favor:** privado. Nada sale de tu computadora. Cada agente con una voz distinta. Sin costo.
- **En contra:** más trabajo. Hay que bajar modelos grandes (cientos de MB). Necesita una computadora con fuerza. Puede tardar un poco en responder.
- **Nota:** la pregunta de la tarjeta gráfica solo importa más adelante, si pasamos al Camino B.
  Ahora no es una decisión abierta.

### Camino C: mezcla con un servicio pago (mejor calidad, cuesta dinero)

- Empezar con A o B. Después, darle a un agente una voz paga (por ejemplo, ElevenLabs).
- **A favor:** voces muy naturales. Poca demora.
- **En contra:** cuesta dinero cada minuto. Necesita una cuenta y una clave. Tu audio sale a otra empresa.
- **Aplazado: se revisa solo cuando toque pagar.** No se usan servicios pagos, cuentas ni claves.

**Mi sugerencia:** empezar con **A** para oír y ver que todo funciona. Luego pasar a **B**. Dejar **C** para cuando quieras una voz especial.

**Estado de la voz: decidido.** El prototipo usa el Camino A, solo en tu computadora, nunca a Google.
El Camino C (pago) queda aplazado.

---

## Otras decisiones

**Ya no quedan decisiones abiertas.**

1. **Botones solo para el organizador. Decidido:** estos 4 botones son solo para una **persona** organizadora (Felipe), nunca para un agente organizador: «Mandar a trabajar solo», «Pedir que vuelva», «Agregar agente de prueba» y «Volver a modo normal». *(Hecho.)*
   - **Agentes que trabajan solos. Decidido:** cuando un agente termina su tarea, vuelve solo al salón y avisa que volvió. Y Felipe puede llamarlo cuando quiera para ver dónde va. *(Todavía no está hecho.)*
2. **Aviso grande de «Baño».** Está **encendido**: en los últimos 5 minutos sale arriba para todos. **Decidido: se queda.**
3. **Frenos de los agentes.** Hoy: cada agente espera **8 segundos** entre mensajes, y como máximo **6 mensajes seguidos** de agentes sin que hable una persona. **Decidido: la espera de 8 segundos se queda por ahora y se ajusta después según conversaciones reales. El tope de 6 mensajes también se queda.**
4. **Reloj naranja.** Se pone naranja para **cualquier** persona en «Baño». **Decidido: se sigue mostrando a todos durante el Baño (como hoy).**
5. **Reportes de vacíos durante «Baño».** No se pueden marcar como revisados mientras estás en «Baño». **Decidido: está bien así; se marcan como revisados después de «Ya volví».**
6. **Copiar el proyecto.** Hoy está solo en mi computadora. **Decidido: copiar el proyecto al NAS Synology de Felipe. Ruta de copia pendiente.**
7. **Subir a GitHub.** **Decidido: por ahora se puede usar GitHub mientras arreglamos el NAS. El NAS sigue siendo el destino. Sin secretos ni claves, sin Actions ni despliegues.** Más adelante Felipe decide si GitHub se queda.
