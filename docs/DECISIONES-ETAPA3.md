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
- **Necesito saber:** ¿aceptas que la voz vaya a Google, o solo en tu computadora?

### Camino B: todo en tu computadora (gratis, mejor calidad)

- Oír con **faster-whisper**. Hablar con **Kokoro** o **Piper**. Audio con **WebRTC**.
- **A favor:** privado. Nada sale de tu computadora. Cada agente con una voz distinta. Sin costo.
- **En contra:** más trabajo. Hay que bajar modelos grandes (cientos de MB). Necesita una computadora con fuerza. Puede tardar un poco en responder.
- **Necesito saber:** ¿qué computadora vas a usar? ¿Tiene tarjeta gráfica?

### Camino C: mezcla con un servicio pago (mejor calidad, cuesta dinero)

- Empezar con A o B. Después, darle a un agente una voz paga (por ejemplo, ElevenLabs).
- **A favor:** voces muy naturales. Poca demora.
- **En contra:** cuesta dinero cada minuto. Necesita una cuenta y una clave. Tu audio sale a otra empresa.
- **Necesito saber:** tu **OK**, cuál servicio y un límite de gasto al mes.

**Mi sugerencia:** empezar con **A** para oír y ver que todo funciona. Luego pasar a **B**. Dejar **C** para cuando quieras una voz especial.

---

## Otras decisiones para mañana

1. **Botones solo para el organizador.** Hoy cualquier persona puede: mandar a un agente a trabajar solo, pedir que vuelva, agregar agentes de prueba y volver un agente a modo normal. ¿Alguno debe ser solo tuyo?
2. **Aviso grande de «Baño».** Hoy está **encendido**: en los últimos 5 minutos sale arriba para todos. ¿Lo dejamos o lo quitamos?
3. **Frenos de los agentes.** Hoy: cada agente espera **8 segundos** entre mensajes, y como máximo **6 mensajes seguidos** de agentes sin que hable una persona. ¿Te parecen bien estos números?
4. **Reloj naranja.** Hoy se pone naranja para **cualquier** persona en «Baño». ¿Solo en tu recuadro?
5. **Reportes de vacíos durante «Baño».** Hoy no se pueden marcar como revisados mientras estás en «Baño». ¿Está bien así?
6. **Copiar el proyecto a tu computadora.** Hoy está solo en mi computadora. ¿Te lo copio a la tuya? ¿En qué carpeta?
7. **Subir a GitHub.** ¿Subo el código a tu repositorio `salon-comunal`? Para eso necesito tu OK y reconectar GitHub.
