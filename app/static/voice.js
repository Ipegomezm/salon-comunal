// Voz (etapa 3, prototipo): dictar tu mensaje con la voz.
//
// REGLA DECIDIDA POR FELIPE: tu audio se queda SOLO en tu computadora. Nunca va a Google
// ni a ningún servicio en internet.
// - Solo se usa el reconocimiento del navegador con `processLocally = true`.
// - Si el navegador no puede hacerlo en tu computadora, la voz NO se usa y sale un aviso.
// - No hay ningún "plan B" en la nube. Este archivo no hace llamadas a internet.
//
// El texto reconocido se escribe en la caja de mensaje; tú decides si lo envías.
const Voz = (() => {
  const IDIOMA = "es-ES";

  const MENSAJES = {
    sinApi: "Tu navegador no puede reconocer la voz. La voz queda apagada.",
    sinLocal: "Tu navegador no puede reconocer la voz solo en tu computadora. " +
      "Para no mandar tu audio a internet, la voz queda apagada. Prueba con Chrome 139 o más nuevo.",
    noDisponible: "El español no se puede reconocer en tu computadora con este navegador. " +
      "La voz queda apagada. Tu audio no se manda a internet.",
    descargable: "Falta bajar el español a tu computadora (solo una vez). Toca «Bajar español».",
    bajando: "Bajando el español a tu computadora…",
    listo: "Listo. Toca «Hablar» y di tu mensaje.",
    escuchando: "Te escucho… (solo en tu computadora)",
    error: "No se pudo usar la voz. Tu audio no se mandó a internet.",
  };

  function constructorDelNavegador(win) {
    win = win || (typeof window !== "undefined" ? window : {});
    return win.SpeechRecognition || win.webkitSpeechRecognition || null;
  }

  // ¿Este navegador puede reconocer la voz SOLO en tu computadora?
  function soportaLocal(Ctor) {
    return !!Ctor && !!Ctor.prototype && ("processLocally" in Ctor.prototype) &&
      typeof Ctor.available === "function";
  }

  // Revisa si se puede usar. Devuelve { estado, mensaje }.
  // estado: "listo" | "descargable" | "apagado"
  async function revisar(Ctor) {
    if (!Ctor) return { estado: "apagado", mensaje: MENSAJES.sinApi };
    if (!soportaLocal(Ctor)) return { estado: "apagado", mensaje: MENSAJES.sinLocal };
    let r;
    try {
      r = await Ctor.available({ langs: [IDIOMA], processLocally: true });
    } catch (e) {
      return { estado: "apagado", mensaje: MENSAJES.noDisponible };
    }
    if (r === "available") return { estado: "listo", mensaje: MENSAJES.listo };
    if (r === "downloadable" || r === "downloading") return { estado: "descargable", mensaje: MENSAJES.descargable };
    return { estado: "apagado", mensaje: MENSAJES.noDisponible };
  }

  // Baja el paquete de español al navegador (no manda audio). Solo si la persona lo pide.
  async function bajarIdioma(Ctor) {
    if (!soportaLocal(Ctor) || typeof Ctor.install !== "function") return false;
    try {
      return !!(await Ctor.install({ langs: [IDIOMA], processLocally: true }));
    } catch (e) {
      return false;
    }
  }

  // Crea el reconocedor, SIEMPRE en tu computadora. Si no se puede asegurar, no lo crea.
  function crearReconocedor(Ctor) {
    if (!soportaLocal(Ctor)) return null;
    const rec = new Ctor();
    rec.processLocally = true;
    if (rec.processLocally !== true) return null;   // el navegador no lo aceptó: no se usa
    rec.lang = IDIOMA;
    rec.continuous = false;
    rec.interimResults = false;
    return rec;
  }

  // Escucha una frase. alTexto(texto) recibe lo reconocido; alMensaje(texto) muestra avisos.
  async function escuchar(Ctor, alTexto, alMensaje) {
    const r = await revisar(Ctor);
    if (r.estado !== "listo") { alMensaje(r.mensaje); return null; }
    const rec = crearReconocedor(Ctor);
    if (!rec) { alMensaje(MENSAJES.sinLocal); return null; }
    rec.onresult = (ev) => {
      const res = ev.results && ev.results[0] && ev.results[0][0];
      if (res && res.transcript) alTexto(res.transcript);
    };
    rec.onerror = () => alMensaje(MENSAJES.error);
    alMensaje(MENSAJES.escuchando);
    rec.start();
    return rec;
  }

  return { IDIOMA, MENSAJES, constructorDelNavegador, soportaLocal, revisar, bajarIdioma, crearReconocedor, escuchar };
})();

if (typeof module !== "undefined") module.exports = Voz;   // para las pruebas
