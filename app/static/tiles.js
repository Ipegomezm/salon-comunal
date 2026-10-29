// Vista tipo Zoom (etapa 2): un recuadro por participante, sin video.
//
// Niveles de voz: cada recuadro dibuja sus ondas a partir de un "nivel" entre 0 y 1.
// Hoy el nivel es SIMULADO a partir del texto que se está "diciendo".
// En la etapa 3, el audio real solo tiene que llamar a:
//     Recuadros.ponerNivel(idParticipante, nivel)   // nivel de 0 a 1, muchas veces por segundo
// y las ondas lo seguirán (el nivel real reemplaza al simulado).
const Recuadros = (() => {
  const BARRAS = 7;
  const reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");
  const recuadros = new Map();     // id -> { el, barras, ... }
  const fuentes = new Map();       // id -> función(ahora) => nivel 0..1, o null cuando terminó
  const nivelesReales = new Map(); // id -> { nivel, t }

  function iniciales(nombre) {
    const partes = nombre.trim().split(/\s+/);
    return ((partes[0] || "?")[0] + (partes[1] ? partes[1][0] : "")).toUpperCase();
  }

  function colorDe(texto) {
    let h = 0;
    for (const c of texto) h = (h * 31 + c.charCodeAt(0)) % 360;
    return `hsl(${h} 45% 45%)`;
  }

  // Nivel simulado: recorre el texto letra por letra; las vocales "suenan" más.
  function fuenteDeTexto(texto, duracionMs) {
    const inicio = performance.now();
    const letras = [...texto];
    return (ahora) => {
      const pasado = ahora - inicio;
      if (pasado >= duracionMs) return null;
      const i = Math.floor((pasado / duracionMs) * letras.length);
      const c = (letras[i] || " ").toLowerCase();
      let base = /[aeiouáéíóú]/.test(c) ? 0.9 : /[a-zñ]/.test(c) ? 0.55 : 0.12;
      return Math.min(1, base * (0.75 + 0.25 * Math.sin(ahora / 70)));
    };
  }

  function duracionDeTexto(texto, segundosPorLetra) {
    const s = Math.min(Math.max(texto.length * (segundosPorLetra || 0.055), 1.2), 9);
    return s * 1000;
  }

  function crear(p) {
    const el = document.createElement("div");
    el.className = "recuadro";
    el.innerHTML = `
      <div class="cara"><span class="iniciales"></span><span class="icono-pausa" aria-hidden="true">⏸</span></div>
      <div class="ondas" aria-hidden="true">${"<i></i>".repeat(BARRAS)}</div>
      <div class="nombre"></div>
      <div class="rol"></div>
      <div class="estado"></div>
      <div class="reloj" aria-label="Tiempo fuera"></div>`;
    const r = { el, barras: [...el.querySelectorAll(".ondas i")] };
    recuadros.set(p.id, r);
    return r;
  }

  // Dibuja o actualiza los recuadros sin recrearlos (para que la luz no se reinicie).
  function actualizar(contenedor, s, yo) {
    const vistos = new Set();
    for (const p of s.participants) {
      vistos.add(p.id);
      const r = recuadros.get(p.id) || crear(p);
      if (r.el.parentNode !== contenedor) contenedor.append(r.el);
      const cara = r.el.querySelector(".cara");
      cara.style.background = colorDe(p.name);
      r.el.querySelector(".iniciales").textContent = iniciales(p.name);
      r.el.querySelector(".nombre").textContent = p.name + (p.id === yo ? " (tú)" : "");
      const roles = [p.kind === "agente" ? "Agente" : "Persona"];
      if (p.organizer) roles.push("organizador");
      r.el.querySelector(".rol").textContent = roles.join(" · ");

      const tiene = p.id === s.speaker;
      const pide = s.queue.includes(p.id);
      const pendiente = p.status === "pendiente";
      let estado = "";
      if (p.away) estado = "Vuelvo en un rato";
      else if (pendiente) estado = "Espera aprobación";
      else if (s.paused) estado = "En pausa";
      else if (tiene) estado = "Tiene la palabra";
      else if (pide) estado = "Pide la palabra";
      else if (p.autonomous) estado = "Trabajando solo";
      if (p.mode === "rapido") estado += (estado ? " · " : "") + "modo rápido";
      r.el.querySelector(".estado").textContent = estado;

      r.el.classList.toggle("pide", pide && !s.paused);
      r.el.classList.toggle("tiene", tiene && !s.paused);
      r.el.classList.toggle("pendiente", pendiente);
      r.el.classList.toggle("pausa", s.paused);
      r.el.classList.toggle("solo", p.autonomous);
      r.el.classList.toggle("bano", !!p.away);
      // Reloj de «Baño»: se guarda el tiempo fuera que mandó el servidor y se sigue contando aquí.
      r.fueraDesde = p.away && p.away_seconds !== null ? performance.now() - p.away_seconds * 1000 : null;
      r.limite = s.bathroom_limit;
      pintarReloj(r);
    }
    for (const [id, r] of recuadros) {
      if (!vistos.has(id)) { r.el.remove(); recuadros.delete(id); fuentes.delete(id); }
    }
  }

  function pintarReloj(r) {
    const reloj = r.el.querySelector(".reloj");
    if (r.fueraDesde === null || r.fueraDesde === undefined) { reloj.textContent = ""; return; }
    const seg = Math.max(0, Math.floor((performance.now() - r.fueraDesde) / 1000));
    const mm = String(Math.floor(seg / 60)).padStart(2, "0");
    const ss = String(seg % 60).padStart(2, "0");
    reloj.textContent = `${mm}:${ss}`;
    // Naranja en los últimos 5 minutos antes del límite.
    reloj.classList.toggle("naranja", r.limite - seg <= 300);
  }
  setInterval(() => { for (const r of recuadros.values()) pintarReloj(r); }, 1000);

  // Se llama con cada mensaje nuevo de la transcripción.
  function alHablar(entrada, segundosPorLetra) {
    if (!entrada.author_id) return;
    fuentes.clear();   // nunca dos hablando a la vez: el nuevo mensaje corta las ondas anteriores
    fuentes.set(entrada.author_id, fuenteDeTexto(entrada.text, duracionDeTexto(entrada.text, segundosPorLetra)));
  }

  // Punto de entrada para la etapa 3 (audio real).
  function ponerNivel(id, nivel) {
    nivelesReales.set(id, { nivel: Math.max(0, Math.min(1, nivel)), t: performance.now() });
  }

  function nivelDe(id, ahora) {
    const real = nivelesReales.get(id);
    if (real && ahora - real.t < 300) return real.nivel;
    const f = fuentes.get(id);
    if (!f) return null;
    const n = f(ahora);
    if (n === null) { fuentes.delete(id); return null; }
    return n;
  }

  function cuadro(ahora) {
    for (const [id, r] of recuadros) {
      const nivel = nivelDe(id, ahora);
      const habla = nivel !== null;
      r.el.classList.toggle("hablando", habla);
      if (!habla) continue;
      r.barras.forEach((b, i) => {
        let alto;
        if (reducirMovimiento.matches) {
          alto = 0.5;   // sin movimiento: barras quietas
        } else {
          const forma = 0.55 + 0.45 * Math.sin(ahora / 110 + i * 1.3);
          alto = 0.12 + 0.88 * nivel * forma;
        }
        b.style.transform = `scaleY(${alto.toFixed(3)})`;
      });
    }
    requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);

  return { actualizar, alHablar, ponerNivel };
})();
