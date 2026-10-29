// Página simple del salón. Se conecta por WebSocket y dibuja el estado.
let ws = null;
let yo = null;
let estado = null;
// Si la página se abrió con el link secreto (?organizador=...), guardamos la clave
// y la quitamos de la barra de direcciones para que no quede a la vista.
const params = new URLSearchParams(location.search);
const claveOrganizador = params.get("organizador") || "";
if (claveOrganizador) history.replaceState(null, "", location.pathname);
const $ = (id) => document.getElementById(id);

function enviar(accion, datos = {}) {
  $("error").textContent = "";
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: accion, ...datos }));
}

function nombreDe(id) {
  const p = estado.participants.find((x) => x.id === id);
  return p ? p.name : "?";
}

function el(tag, attrs = {}, ...hijos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "onclick") e.onclick = v; else if (k === "class") e.className = v; else e.setAttribute(k, v);
  }
  for (const h of hijos) e.append(h);
  return e;
}

function dibujar() {
  const s = estado;
  $("palabra").textContent = s.speaker ? nombreDe(s.speaker) + (s.speaker === yo ? " (tú)" : "") : "Nadie";
  $("fila").textContent = s.queue.length ? "Esperan turno: " + s.queue.map(nombreDe).join(", ") : "Nadie espera turno.";

  const lista = $("participantes");
  lista.innerHTML = "";
  for (const p of s.participants) {
    const clases = [];
    if (p.id === s.speaker) clases.push("habla");
    else if (s.queue.includes(p.id)) clases.push("pide");
    if (p.status === "pendiente") clases.push("pendiente");
    const li = el("li", { class: clases.join(" ") });
    li.append(el("strong", {}, p.name + (p.id === yo ? " (tú)" : "")));
    li.append(el("span", { class: "etiqueta" }, p.kind === "agente" ? "agente" : "persona"));
    if (p.id === s.speaker) li.append(el("span", { class: "etiqueta" }, "habla"));
    else if (s.queue.includes(p.id)) li.append(el("span", { class: "etiqueta" }, "pidió la palabra"));
    if (p.organizer) li.append(el("span", { class: "etiqueta org" }, "organizador"));
    if (p.mode === "rapido") li.append(el("span", { class: "etiqueta rapido" }, "modo rápido"));
    if (p.autonomous) li.append(el("span", { class: "etiqueta solo" }, "trabajando solo"));
    if (p.personality) li.append(el("div", { class: "desc" }, p.personality));
    if (p.kind === "agente" && p.status === "pendiente") {
      if (s.you_are_organizer) {
        li.append(el("div", { class: "desc" }, "Espera tu aprobación para entrar."));
        li.append(el("button", { class: "si", onclick: () => enviar("approve_agent", { agent_id: p.id }) }, "Aprobar"));
        li.append(el("button", { class: "no", onclick: () => enviar("reject_agent", { agent_id: p.id }) }, "No aprobar"));
      } else {
        li.append(el("div", { class: "desc" }, "Espera aprobación del organizador."));
      }
    } else if (p.kind === "agente") {
      if (p.autonomous) {
        li.append(el("button", { onclick: () => enviar("end_autonomous", { agent_id: p.id }) }, "Pedir que vuelva"));
      } else {
        li.append(el("button", { onclick: () => {
          const tarea = prompt("¿En qué debe trabajar " + p.name + " por su cuenta?");
          if (tarea) enviar("start_autonomous", { agent_id: p.id, task: tarea });
        } }, "Mandar a trabajar solo"));
      }
      if (p.mode === "rapido") li.append(el("button", { onclick: () => enviar("back_to_normal", { agent_id: p.id }) }, "Volver a modo normal"));
    }
    lista.append(li);
  }

  $("rol").textContent = s.you_are_organizer ? "Entraste como organizador" : "Entraste como invitado";
  const pendientes = s.mode_requests.filter((r) => r.status === "pendiente");
  $("caja-modos").hidden = !s.you_are_organizer || pendientes.length === 0;
  const modos = $("modos");
  modos.innerHTML = "";
  for (const r of pendientes) {
    modos.append(el("li", {},
      el("div", {}, nombreDe(r.agent_id) + " quiere pasar a modo rápido. Motivo: " + r.reason),
      el("button", { class: "si", onclick: () => enviar("decide_mode", { request_id: r.id, approve: true }) }, "Autorizar"),
      el("button", { class: "no", onclick: () => enviar("decide_mode", { request_id: r.id, approve: false }) }, "Negar"),
    ));
  }

  const t = $("transcripcion");
  const abajo = t.scrollHeight - t.scrollTop - t.clientHeight < 40;
  t.innerHTML = "";
  for (const e of s.transcript) {
    const clases = [e.kind, e.author_kind || "", e.mode === "rapido" ? "rapido" : ""].join(" ");
    const li = el("li", { class: clases });
    if (e.kind === "mensaje" || e.kind === "vacio") {
      if (e.kind === "mensaje") li.append(el("span", { class: "autor" }, e.author_name + ": "));
      if (e.mode === "rapido") li.append(el("span", { class: "etiqueta rapido" }, "modo rápido"), " ");
    }
    li.append(el("span", { class: "texto" }, e.text));
    t.append(li);
  }
  if (abajo) t.scrollTop = t.scrollHeight;

  const enFila = s.queue.includes(yo);
  $("btn-pedir").disabled = enFila || s.speaker === yo;
  $("btn-retirar").disabled = !enFila;
  $("btn-soltar").disabled = s.speaker !== yo;
  const hablaAgente = s.speaker && s.participants.find((p) => p.id === s.speaker)?.kind === "agente";
  $("btn-interrumpir").disabled = !hablaAgente;
}

$("form-entrar").onsubmit = (ev) => {
  ev.preventDefault();
  const nombre = $("nombre").value.trim();
  if (!nombre) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    ws.send(JSON.stringify({ action: "join", name: nombre, organizer_token: claveOrganizador }));
    $("estado-conexion").textContent = "Conectado";
  };
  ws.onclose = () => { $("estado-conexion").textContent = "Desconectado. Recarga la página."; };
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.type === "state") {
      yo = d.you; estado = d.state;
      $("entrar").hidden = true; $("salon").hidden = false;
      dibujar();
    } else if (d.type === "error") {
      $("error").textContent = d.message;
    }
  };
};

$("form-mensaje").onsubmit = (ev) => {
  ev.preventDefault();
  const texto = $("mensaje").value.trim();
  if (!texto) return;
  enviar("say", { text: texto });
  $("mensaje").value = "";
};
$("btn-pedir").onclick = () => enviar("request_floor");
$("btn-retirar").onclick = () => enviar("withdraw_floor");
$("btn-soltar").onclick = () => enviar("release_floor");
$("btn-interrumpir").onclick = () => enviar("interrupt");
$("form-agente").onsubmit = (ev) => {
  ev.preventDefault();
  enviar("add_agent", { style: $("estilo").value, name: $("nombre-agente").value });
  $("nombre-agente").value = "";
};
