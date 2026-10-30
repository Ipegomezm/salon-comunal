// Voz de los agentes (etapa 3, prototipo): los agentes leen sus mensajes en voz alta.
//
// REGLA DECIDIDA POR FELIPE: nada sale de su computadora.
// - Solo se usan voces del navegador con `localService === true` (voces instaladas en la computadora).
// - Las voces de red (por ejemplo las "Google ..." de Chrome) mandan el texto a internet:
//   NUNCA se usan. Tampoco la voz "por defecto", porque podría ser de red.
// - Si no hay ninguna voz local en español, sale un aviso y los agentes siguen solo en texto.
// - Solo funciona si el servidor encendió la voz (SALON_VOZ=1). Apagada por defecto.
const VozAgentes = (() => {
  const MENSAJES = {
    sinApi: "Tu navegador no puede leer en voz alta. Los agentes siguen solo en texto.",
    sinVozLocal: "No hay voces en español instaladas en tu computadora. Los agentes siguen solo en texto.",
    lista: (n) => `Los agentes hablan en voz alta con ${n === 1 ? "1 voz" : n + " voces"} de tu computadora.`,
  };

  // ¿Es una voz local en español? (las de red se descartan siempre)
  function esLocalEnEspanol(v) {
    return !!v && v.localService === true &&
      typeof v.lang === "string" && /^es([-_]|$)/i.test(v.lang) &&
      !/google/i.test(v.name || "");   // por si acaso: las "Google" de Chrome son de red
  }

  // Voces locales en español, primero las de España (es-ES).
  function vocesLocales(voces) {
    const locales = (voces || []).filter(esLocalEnEspanol);
    return locales.sort((a, b) => (/^es[-_]es$/i.test(b.lang) ? 1 : 0) - (/^es[-_]es$/i.test(a.lang) ? 1 : 0));
  }

  // Cada agente recibe siempre la misma voz local (si hay varias, se reparten).
  function vozPara(idAgente, locales) {
    if (!locales || !locales.length) return null;
    let h = 0;
    for (const c of String(idAgente)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return locales[h % locales.length];
  }

  // Lee las voces del navegador (a veces llegan un poco después).
  function leerVoces(synth, esperaMs = 1500) {
    return new Promise((resolve) => {
      const ya = synth.getVoices() || [];
      if (ya.length) return resolve(ya);
      let listo = false;
      const fin = () => { if (!listo) { listo = true; resolve(synth.getVoices() || []); } };
      if (typeof synth.addEventListener === "function") synth.addEventListener("voiceschanged", fin, { once: true });
      setTimeout(fin, esperaMs);
    });
  }

  // Prepara la voz de los agentes. cfg.voz viene del servidor (SALON_VOZ).
  // Devuelve { activa, mensaje, decir(idAgente, texto, eventos) }.
  async function preparar(cfg, win, esperaMs) {
    const apagada = { activa: false, mensaje: "", decir: () => null };
    if (!cfg || cfg.voz !== true) return apagada;          // interruptor apagado: no se toca nada
    const synth = win && win.speechSynthesis;
    const Utt = win && win.SpeechSynthesisUtterance;
    if (!synth || !Utt) return { ...apagada, mensaje: MENSAJES.sinApi };
    const locales = vocesLocales(await leerVoces(synth, esperaMs));
    if (!locales.length) return { ...apagada, mensaje: MENSAJES.sinVozLocal };

    // Lee un texto con la voz local del agente. eventos: { alEmpezar, alPalabra, alTerminar }
    function decir(idAgente, texto, eventos = {}) {
      const voz = vozPara(idAgente, locales);
      if (!esLocalEnEspanol(voz) || !texto) return null;   // nunca sin voz local elegida
      const u = new Utt(texto);
      u.voice = voz;
      u.lang = voz.lang;
      u.onstart = () => eventos.alEmpezar && eventos.alEmpezar();
      u.onboundary = () => eventos.alPalabra && eventos.alPalabra();
      u.onend = () => eventos.alTerminar && eventos.alTerminar();
      u.onerror = () => eventos.alTerminar && eventos.alTerminar();
      synth.speak(u);
      return u;
    }
    return { activa: true, mensaje: MENSAJES.lista(locales.length), decir, voces: locales };
  }

  return { MENSAJES, esLocalEnEspanol, vocesLocales, vozPara, preparar };
})();

if (typeof module !== "undefined") module.exports = VozAgentes;   // para las pruebas
