// Prueba de la voz de los agentes: SOLO voces locales (localService === true), nunca de red.
// Se corre desde pytest (tests/test_voice_rule.py) con Node. Sin red.
const assert = require("assert");
const VA = require("../../app/static/agent_voice.js");

const GOOGLE = { name: "Google español", lang: "es-ES", localService: false };
const RED = { name: "Microsoft Elvira Online (Natural)", lang: "es-ES", localService: false };
const SIN_DATO = { name: "Rara", lang: "es-ES" };                       // localService no dice nada
const GOOGLE_LOCAL = { name: "Google español", lang: "es-ES", localService: true };
const MONICA = { name: "Mónica", lang: "es-ES", localService: true };
const PAULINA = { name: "Paulina", lang: "es-MX", localService: true };
const INGLES = { name: "Samantha", lang: "en-US", localService: true };

function navegador(voces, { trampa = false } = {}) {
  const registro = { hablados: [], tocado: false };
  const synth = {
    getVoices() { registro.tocado = true; return voces; },
    addEventListener() {},
    speak(u) { registro.hablados.push(u); u.onstart(); u.onboundary(); u.onend(); },
  };
  function Utt(texto) { this.text = texto; }
  const win = trampa
    ? new Proxy({}, { get() { registro.tocado = true; throw new Error("no se debe tocar la voz"); } })
    : { speechSynthesis: synth, SpeechSynthesisUtterance: Utt };
  return { win, registro };
}

(async () => {
  // 1) Filtro: solo locales en español; red, sin dato, "Google" e inglés quedan fuera.
  const locales = VA.vocesLocales([GOOGLE, RED, SIN_DATO, GOOGLE_LOCAL, PAULINA, MONICA, INGLES]);
  assert.deepStrictEqual(locales.map((v) => v.name), ["Mónica", "Paulina"]);
  for (const v of [GOOGLE, RED, SIN_DATO, GOOGLE_LOCAL, INGLES]) assert.strictEqual(VA.esLocalEnEspanol(v), false);

  // 2) Interruptor apagado: no se toca speechSynthesis para nada.
  let n = navegador([], { trampa: true });
  let va = await VA.preparar({ voz: false }, n.win, 10);
  assert.strictEqual(va.activa, false);
  assert.strictEqual(va.decir("a1", "hola"), null);
  assert.strictEqual(n.registro.tocado, false);
  va = await VA.preparar(undefined, n.win, 10);
  assert.strictEqual(va.activa, false);

  // 3) Solo voces de red: aviso en español, solo texto, nunca se habla.
  n = navegador([GOOGLE, RED, SIN_DATO]);
  va = await VA.preparar({ voz: true }, n.win, 10);
  assert.strictEqual(va.activa, false);
  assert.strictEqual(va.mensaje, VA.MENSAJES.sinVozLocal);
  assert.strictEqual(va.decir("a1", "hola"), null);
  assert.strictEqual(n.registro.hablados.length, 0);

  // 4) Sin API de voz: aviso y solo texto.
  va = await VA.preparar({ voz: true }, {}, 10);
  assert.strictEqual(va.activa, false);
  assert.strictEqual(va.mensaje, VA.MENSAJES.sinApi);

  // 5) Con una voz local: se habla SIEMPRE con esa voz, y los eventos llegan en orden.
  n = navegador([GOOGLE, MONICA, RED]);
  va = await VA.preparar({ voz: true }, n.win, 10);
  assert.strictEqual(va.activa, true);
  const eventos = [];
  const u = va.decir("a2", "Hola a todos", {
    alEmpezar: () => eventos.push("inicio"), alPalabra: () => eventos.push("palabra"), alTerminar: () => eventos.push("fin"),
  });
  assert.ok(u);
  assert.strictEqual(u.voice, MONICA);
  assert.strictEqual(u.voice.localService, true);
  assert.deepStrictEqual(eventos, ["inicio", "palabra", "fin"]);
  for (const h of n.registro.hablados) assert.strictEqual(h.voice.localService, true);

  // 6) Cada agente tiene siempre la misma voz, y siempre local.
  n = navegador([MONICA, PAULINA, GOOGLE]);
  va = await VA.preparar({ voz: true }, n.win, 10);
  for (const id of ["a1", "a2", "a3", "a7", "a12"]) {
    const v1 = va.decir(id, "uno").voice, v2 = va.decir(id, "dos").voice;
    assert.strictEqual(v1, v2);
    assert.ok([MONICA, PAULINA].includes(v1));
  }
  assert.ok(n.registro.hablados.every((h) => h.voice.localService === true && !/google/i.test(h.voice.name)));

  console.log("OK voz de agentes solo local");
})().catch((e) => { console.error(e); process.exit(1); });
