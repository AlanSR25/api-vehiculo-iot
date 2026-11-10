/**
 * main.js - Orquestador principal de la aplicación de control IoT
 */

import { CONFIG } from "./config.js?v=20261110";
import { apiService } from "./services/apiService.js";
import { wsService, WsState } from "./services/wsService.js";
import { appState } from "./state/appState.js";
import { VirtualJoystick } from "./components/joystick.js";

// Mapeo unificado de comandos del vehículo (1 al 9)
const COMANDO_MAP = {
  AVANZAR: 1,
  RETROCEDER: 2,
  IZQUIERDA: 3,
  DERECHA: 4,
  SUBIR: 5,
  BAJAR: 6,
  LUZ: 7,
  GRABAR: 8,
  DETENER: 9,
  NEUTRAL: 9,
};

// Elementos DOM
const dom = {
  vehiculoNombre: document.getElementById("vehiculoNombre"),
  vehiculoModelo: document.getElementById("vehiculoModelo"),

  // 3 Indicadores obligatorios
  wsStatusBadge: document.getElementById("wsStatusBadge"),
  apiStatusBadge: document.getElementById("apiStatusBadge"),
  rdsStatusBadge: document.getElementById("rdsStatusBadge"),

  // Paneles y controles
  joystickContainer: document.getElementById("joystickContainer"),
  joystickDirectionText: document.getElementById("joystickDirectionText"),
  btnDetener: document.getElementById("btnDetener"),

  // Botones secundarios
  btnSubir: document.getElementById("btnSubir"),
  btnBajar: document.getElementById("btnBajar"),
  btnLuz: document.getElementById("btnLuz"),
  btnGrabar: document.getElementById("btnGrabar"),

  // Demos
  selectDemo: document.getElementById("selectDemo"),
  btnIniciarDemo: document.getElementById("btnIniciarDemo"),
  btnCancelarDemo: document.getElementById("btnCancelarDemo"),
  demoStatusCard: document.getElementById("demoStatusCard"),
  demoStepText: document.getElementById("demoStepText"),

  // Log de acciones
  logSolicitud: document.getElementById("logSolicitud"),
  logHttp: document.getElementById("logHttp"),
  logWs: document.getElementById("logWs"),
};

// 1. Inicialización
document.addEventListener("DOMContentLoaded", async () => {
  initJoystick();
  bindButtons();
  initWebSocket();
  initHealthPolling();
  await loadInitialData();
});

// 2. Configurar Joystick Virtual
function initJoystick() {
  new VirtualJoystick(dom.joystickContainer, (direction) => {
    dom.joystickDirectionText.textContent = direction;
    const codigoComando = COMANDO_MAP[direction];
    if (codigoComando) {
      ejecutarComando(codigoComando, `JOYSTICK_${direction}`);
    }
  });
}

// 3. Asociar Botones Secundarios
function bindButtons() {
  // DETENER prioritario
  dom.btnDetener.addEventListener("click", () => {
    ejecutarComando(COMANDO_MAP.DETENER, "BOTON_DETENER_PRIORITARIO");
    if (appState.demoActiva) {
      apiService.cancelarDemo().catch(() => {});
    }
  });

  // Accesorios
  dom.btnSubir.addEventListener("click", () => ejecutarComando(COMANDO_MAP.SUBIR, "BOTON_SUBIR"));
  dom.btnBajar.addEventListener("click", () => ejecutarComando(COMANDO_MAP.BAJAR, "BOTON_BAJAR"));
  dom.btnLuz.addEventListener("click", () => ejecutarComando(COMANDO_MAP.LUZ, "BOTON_LUZ"));
  dom.btnGrabar.addEventListener("click", () => ejecutarComando(COMANDO_MAP.GRABAR, "BOTON_GRABAR_MEMORIA"));

  // DEMO
  dom.btnIniciarDemo.addEventListener("click", async () => {
    const idDemo = dom.selectDemo.value;
    if (!idDemo) return;
    try {
      dom.btnIniciarDemo.disabled = true;
      dom.btnCancelarDemo.disabled = false;
      actualizarLog("DEMO Iniciar", "Enviando...", "Esperando WSS...");
      const res = await apiService.iniciarDemo(idDemo);
      appState.demoActiva = true;
      actualizarLog(`DEMO Iniciar (${idDemo})`, "202 Aceptada", "WSS notificará pasos");
    } catch (err) {
      actualizarLog(`DEMO Error`, `Fallo: ${err.message}`, "Sin evento");
      dom.btnIniciarDemo.disabled = false;
      dom.btnCancelarDemo.disabled = true;
    }
  });

  dom.btnCancelarDemo.addEventListener("click", async () => {
    try {
      await apiService.cancelarDemo();
      ejecutarComando(COMANDO_MAP.DETENER, "CANCELAR_DEMO");
      actualizarLog("DEMO Cancelar", "200 Enviada", "Cancelando...");
    } catch (err) {
      actualizarLog("DEMO Cancelar", `Error: ${err.message}`, "-");
    }
  });
}

// 4. Ejecución unificada de comandos
async function ejecutarComando(codigo, origen = "FRONTEND-WEB") {
  appState.ultimaAccion.solicitada = `Comando ${codigo} (${origen})`;
  actualizarLog(`Comando ${codigo}`, "Enviando POST...", "Pendiente WSS...");

  try {
    const res = await apiService.enviarMovimiento(codigo, CONFIG.VEHICLE_ID, origen);
    actualizarLog(
      `Comando ${codigo} [${res.comando || "OK"}]`,
      `HTTP 200 Aceptado`,
      appState.ultimaAccion.eventoWs || "Esperando WSS..."
    );
  } catch (err) {
    actualizarLog(`Comando ${codigo}`, `Error: ${err.message}`, "No emitido");
  }
}

// 5. Gestión del WebSocket
function initWebSocket() {
  wsService.onStateChange((state) => {
    appState.wsEstado = state;
    renderWsStatus(state);
  });

  wsService.onMessage((msg) => {
    handleWebSocketMessage(msg);
  });

  wsService.connect();
}

function handleWebSocketMessage(msg) {
  const evento = msg.evento || "EVENTO_RECIBIDO";
  const cmd = msg.comando || msg.codigo || "-";
  appState.ultimaAccion.eventoWs = `${evento}: ${cmd}`;

  dom.logWs.textContent = `${evento} (${cmd})`;
  dom.logWs.className = "badge bg-success-subtle text-success border border-success-subtle";

  // Control visual de DEMO
  if (evento === "DEMO_INICIO") {
    appState.demoActiva = true;
    dom.demoStatusCard.classList.remove("d-none");
    dom.demoStepText.textContent = `Demo iniciada. Pasos: ${msg.total_movimientos || "-"}`;
    dom.btnIniciarDemo.disabled = true;
    dom.btnCancelarDemo.disabled = false;
  } else if (evento === "MOVIMIENTO_DEMO") {
    dom.demoStepText.textContent = `Paso ${msg.orden}: ${msg.comando} (${msg.duracion_ms} ms)`;
  } else if (evento === "DEMO_FINALIZADA" || evento === "DEMO_CANCELADA") {
    appState.demoActiva = false;
    dom.demoStepText.textContent = evento === "DEMO_FINALIZADA" ? "Secuencia finalizada" : "Secuencia cancelada";
    dom.btnIniciarDemo.disabled = false;
    dom.btnCancelarDemo.disabled = true;
    setTimeout(() => dom.demoStatusCard.classList.add("d-none"), 3500);
  }
}

// 6. Polling seguro de salud (/health)
function initHealthPolling() {
  const check = async () => {
    try {
      const data = await apiService.getHealth();
      renderApiStatus(data.api === "ok" ? "DISPONIBLE" : "NO_DISPONIBLE");
      renderRdsStatus(data.base_de_datos === "ok" ? "DISPONIBLE" : "NO_DISPONIBLE");
    } catch {
      renderApiStatus("NO_DISPONIBLE");
      renderRdsStatus("NO_DISPONIBLE");
    }
  };

  check();
  setInterval(check, CONFIG.HEALTH_CHECK_INTERVAL_MS);
}

// 7. Carga de Catálogos Iniciales
async function loadInitialData() {
  try {
    const [vehiculo, demos] = await Promise.all([
      apiService.getVehiculo().catch(() => null),
      apiService.getDemos().catch(() => []),
    ]);

    if (vehiculo) {
      dom.vehiculoNombre.textContent = vehiculo.nombre || "Excavadora IoT";
      dom.vehiculoModelo.textContent = `${vehiculo.modelo || "ESP32"} · ${vehiculo.microcontrolador || "IoT"}`;
    }

    if (demos && demos.length > 0) {
      dom.selectDemo.innerHTML = demos
        .map((d) => `<option value="${d.id_demo}">${d.nombre}</option>`)
        .join("");
    }
  } catch (e) {
    console.error("Error al cargar datos iniciales:", e);
  }
}

// 8. Renderizado de los 3 Indicadores Obligatorios
function renderWsStatus(state) {
  if (state === WsState.ONLINE) {
    dom.wsStatusBadge.className = "badge bg-success";
    dom.wsStatusBadge.innerHTML = '<i class="bi bi-broadcast"></i> En línea';
  } else if (state === WsState.CONNECTING) {
    dom.wsStatusBadge.className = "badge bg-warning text-dark";
    dom.wsStatusBadge.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Conectando...';
  } else {
    dom.wsStatusBadge.className = "badge bg-danger";
    dom.wsStatusBadge.innerHTML = '<i class="bi bi-wifi-off"></i> Desconectado';
  }
}

function renderApiStatus(status) {
  if (status === "DISPONIBLE") {
    dom.apiStatusBadge.className = "badge bg-success";
    dom.apiStatusBadge.innerHTML = '<i class="bi bi-cloud-check"></i> Disponible';
  } else if (status === "COMPROBANDO") {
    dom.apiStatusBadge.className = "badge bg-secondary";
    dom.apiStatusBadge.innerHTML = '<i class="bi bi-hourglass-split"></i> Comprobando';
  } else {
    dom.apiStatusBadge.className = "badge bg-danger";
    dom.apiStatusBadge.innerHTML = '<i class="bi bi-cloud-slash"></i> No disponible';
  }
}

function renderRdsStatus(status) {
  if (status === "DISPONIBLE") {
    dom.rdsStatusBadge.className = "badge bg-success";
    dom.rdsStatusBadge.innerHTML = '<i class="bi bi-database-check"></i> Disponible';
  } else if (status === "NO_DISPONIBLE") {
    dom.rdsStatusBadge.className = "badge bg-danger";
    dom.rdsStatusBadge.innerHTML = '<i class="bi bi-database-slash"></i> No disponible';
  } else {
    dom.rdsStatusBadge.className = "badge bg-secondary";
    dom.rdsStatusBadge.innerHTML = '<i class="bi bi-question-circle"></i> Sin verificar';
  }
}

function actualizarLog(solicitud, http, ws) {
  dom.logSolicitud.textContent = solicitud;
  dom.logHttp.textContent = http;
  if (ws) dom.logWs.textContent = ws;
}

