// Prueba de la regla de voz: SOLO en tu computadora, nunca en la nube.
// Se corre desde pytest (tests/test_voice_rule.py) con Node.
const assert = require("assert");
const Voz = require("../../app/static/voice.js");

function fake({ conLocal = true, disponible = "available", aceptaLocal = true } = {}) {
  const registro = { creados: [], starts: 0, available: [], install: [] };
  function Ctor() {
    let local = false;
    const inst = { start() { registro.starts++; inst.startedLocal = inst.processLocally; } };
    Object.defineProperty(inst, "processLocally", {
      get: () => local, set: (v) => { if (aceptaLocal) local = v; }, enumerable: true,
    });
    registro.creados.push(inst);
    return inst;
  }
  if (conLocal) {
    Ctor.prototype.processLocally = false;
    Ctor.available = async (opts) => { registro.available.push(opts); return disponible; };
    Ctor.install = async (opts) => { registro.install.push(opts); return true; };
  }
  return { Ctor, registro };
}

(async () => {
  const msgs = [];
  const aviso = (t) => msgs.push(t);
  const texto = () => {};

  // 1) Sin API de voz: no se escucha.
  assert.strictEqual(await Voz.escuchar(null, texto, aviso), null);

  // 2) El navegador no puede hacerlo en la computadora: NUNCA se empieza (nada de nube).
  let f = fake({ conLocal: false });
  assert.strictEqual(await Voz.escuchar(f.Ctor, texto, aviso), null);
  assert.strictEqual(f.registro.starts, 0);
  assert.strictEqual(f.registro.creados.length, 0);
  assert.strictEqual(msgs.at(-1), Voz.MENSAJES.sinLocal);

  // 3) Idioma no disponible en la computadora: no se empieza.
  f = fake({ disponible: "unavailable" });
  assert.strictEqual(await Voz.escuchar(f.Ctor, texto, aviso), null);
  assert.strictEqual(f.registro.starts, 0);
  assert.deepStrictEqual(f.registro.available[0], { langs: ["es-ES"], processLocally: true });

  // 4) Falta bajar el idioma: no se empieza hasta bajarlo (y se baja pidiendo "solo local").
  f = fake({ disponible: "downloadable" });
  assert.strictEqual(await Voz.escuchar(f.Ctor, texto, aviso), null);
  assert.strictEqual(f.registro.starts, 0);
  assert.strictEqual(await Voz.bajarIdioma(f.Ctor), true);
  assert.deepStrictEqual(f.registro.install[0], { langs: ["es-ES"], processLocally: true });

  // 5) El navegador no acepta processLocally = true: no se crea el reconocedor.
  f = fake({ aceptaLocal: false });
  assert.strictEqual(await Voz.escuchar(f.Ctor, texto, aviso), null);
  assert.strictEqual(f.registro.starts, 0);

  // 6) Todo bien: se empieza, y SIEMPRE con processLocally = true y en español.
  f = fake();
  const rec = await Voz.escuchar(f.Ctor, texto, aviso);
  assert.ok(rec);
  assert.strictEqual(f.registro.starts, 1);
  assert.strictEqual(rec.startedLocal, true);
  assert.strictEqual(rec.lang, "es-ES");

  console.log("OK voz solo local");
})().catch((e) => { console.error(e); process.exit(1); });
