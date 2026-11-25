/**
 * main.js - Orquestador integral de la Plataforma IoT (Prácticas 4.1, 4.2 y 4.3)
 * - Navegación fluida: CONTROL | MONITOREO | ADMINISTRACIÓN
 * - Autenticación JWT, roles (ADMIN, USUARIO, INVITADO) y autorización por recurso.
 * - WSS autenticado y dinámico por vehículo sin conexiones duplicadas.
 * - Reserva temporal de Invitado con cuenta regresiva y detención segura automática.
 */

import { CONFIG } from "./config.js?v=20261125a";
import { apiService } from "./services/apiService.js?v=20261125a";
import { wsService, WsState } from "./services/wsService.js?v=20261125a";
import { appState } from "./state/appState.js?v=20261125a";
import { VirtualJoystick } from "./components/joystick.js?v=20261125a";
import { monitoreoManager } from "./components/monitoreo.js?v=20261125a";
import { administracionManager } from "./components/administracion.js?v=20261125a";

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

let currentUser = null;
let activeVehicleId = CONFIG.VEHICLE_ID;
let activeVehicleName = "Excavadora IoT";
let guestTimerInterval = null;
let guestSecondsLeft = 0;
let loginModal = null;

const dom = {
  // Pestañas
  tabBtnControl: document.getElementById("tabBtnControl"),
  tabBtnMonitoreo: document.getElementById("tabBtnMonitoreo"),
  tabBtnAdmin: document.getElementById("tabBtnAdmin"),
  tabLabelAdmin: document.getElementById("tabLabelAdmin"),
  vistaControl: document.getElementById("vistaControl"),
  vistaMonitoreo: document.getElementById("vistaMonitoreo"),
  vistaAdmin: document.getElementById("vistaAdministracion"),

  // Header & Sesión
  vehiculoNombre: document.getElementById("vehiculoNombre"),
  vehiculoModelo: document.getElementById("vehiculoModelo"),
  headerVehiculoSelect: document.getElementById("headerVehiculoSelect"),
  headerVehiculoBadge: document.getElementById("headerVehiculoBadge"),
  authUserBadge: document.getElementById("authUserBadge"),
  btnAuthAction: document.getElementById("btnAuthAction"),
  alertaSinSesion: document.getElementById("alertaSinSesion"),
  btnAbrirLoginAlerta: document.getElementById("btnAbrirLoginAlerta"),
  btnIrCatalogoAlerta: document.getElementById("btnIrCatalogoAlerta"),

  // Banner Invitado
  bannerInvitado: document.getElementById("bannerInvitado"),
  bannerInvitadoTexto: document.getElementById("bannerInvitadoTexto"),
  bannerInvitadoTimer: document.getElementById("bannerInvitadoTimer"),
  btnFinalizarInvitado: document.getElementById("btnFinalizarInvitado"),

  // Modal Login
  formLogin: document.getElementById("formLogin"),
  loginCorreo: document.getElementById("loginCorreo"),
  loginPassword: document.getElementById("loginPassword"),
  loginErrorAlert: document.getElementById("loginErrorAlert"),
  btnQuickAdmin: document.getElementById("btnQuickAdmin"),
  btnQuickUsuario: document.getElementById("btnQuickUsuario"),
  btnQuickInvitado: document.getElementById("btnQuickInvitado"),

  // 3 Indicadores
  wsStatusBadge: document.getElementById("wsStatusBadge"),
  apiStatusBadge: document.getElementById("apiStatusBadge"),
  rdsStatusBadge: document.getElementById("rdsStatusBadge"),

  // Control 4.1
  joystickContainer: document.getElementById("joystickContainer"),
  joystickDirectionText: document.getElementById("joystickDirectionText"),
  btnDetener: document.getElementById("btnDetener"),
  btnSubir: document.getElementById("btnSubir"),
  btnBajar: document.getElementById("btnBajar"),
  btnLuz: document.getElementById("btnLuz"),
  btnGrabar: document.getElementById("btnGrabar"),
  cardDemoControl: document.getElementById("cardDemoControl"),
  selectDemo: document.getElementById("selectDemo"),
  btnIniciarDemo: document.getElementById("btnIniciarDemo"),
  btnCancelarDemo: document.getElementById("btnCancelarDemo"),
  demoStatusCard: document.getElementById("demoStatusCard"),
  demoStepText: document.getElementById("demoStepText"),
  logSolicitud: document.getElementById("logSolicitud"),
  logHttp: document.getElementById("logHttp"),
  logWs: document.getElementById("logWs"),
};

// 1. Inicialización
document.addEventListener("DOMContentLoaded", async () => {
  const modalEl = document.getElementById("modalLogin");
  if (modalEl && window.bootstrap) {
    loginModal = new window.bootstrap.Modal(modalEl);
  }

  initNavigationTabs();
  initAuthUI();
  initJoystick();
  bindButtons();
  initWebSocketListeners();
  initHealthPolling();

  // Callbacks del módulo de Administración
  administracionManager.onSelectVehicle = async (id, nombre, goToControl) => {
    await cambiarVehiculoActivo(id, nombre);
    if (goToControl) activarPestana("CONTROL");
  };

  administracionManager.onGuestSessionStarted = async (sesion) => {
    currentUser = apiService.getStoredUser();
    actualizarHeaderSesion();
    iniciarTimerInvitado(sesion);
    await cambiarVehiculoActivo(sesion.id_vehiculo, sesion.nombre_vehiculo);
    activarPestana("CONTROL");
  };

  administracionManager.onDemosChanged = async (idVeh) => {
    if (Number(idVeh) === Number(activeVehicleId)) {
      await cargarDemosVehiculo(activeVehicleId);
    }
  };

  // Restaurar sesión previa de esta pestaña si existe
  await restaurarSesion();
});

// 2. Navegación 3 Pestañas
function initNavigationTabs() {
  dom.tabBtnControl?.addEventListener("click", () => activarPestana("CONTROL"));
  dom.tabBtnMonitoreo?.addEventListener("click", () => {
    activarPestana("MONITOREO");
    monitoreoManager.cargarDatosCompletos();
  });
  dom.tabBtnAdmin?.addEventListener("click", () => {
    activarPestana("ADMIN");
    administracionManager.renderPorRol(currentUser, activeVehicleId);
  });
}

function activarPestana(tab) {
  const map = {
    CONTROL: [dom.tabBtnControl, dom.vistaControl],
    MONITOREO: [dom.tabBtnMonitoreo, dom.vistaMonitoreo],
    ADMIN: [dom.tabBtnAdmin, dom.vistaAdmin],
  };
  Object.entries(map).forEach(([key, [btn, view]]) => {
    const active = key === tab;
    btn?.classList.toggle("active", active);
    btn?.setAttribute("aria-selected", active ? "true" : "false");
    view?.classList.toggle("d-none", !active);
  });
}

// 3. Autenticación y Sesiones
function initAuthUI() {
  dom.btnAuthAction?.addEventListener("click", async () => {
    if (currentUser) {
      await cerrarSesionActual();
    } else {
      loginModal?.show();
    }
  });

  dom.btnAbrirLoginAlerta?.addEventListener("click", () => loginModal?.show());
  dom.btnIrCatalogoAlerta?.addEventListener("click", () => {
    activarPestana("ADMIN");
    administracionManager.renderPorRol(null, null);
  });

  dom.btnFinalizarInvitado?.addEventListener("click", async () => {
    await finalizarModoInvitado();
  });

  dom.headerVehiculoSelect?.addEventListener("change", async (e) => {
    const id = Number(e.target.value);
    const optText = e.target.options[e.target.selectedIndex]?.text || `Unidad #${id}`;
    await cambiarVehiculoActivo(id, optText);
  });

  dom.formLogin?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await ejecutarLogin(dom.loginCorreo.value, dom.loginPassword.value);
  });

  dom.btnQuickAdmin?.addEventListener("click", () => ejecutarLogin("admin@empresa-iot.com", "Admin123!"));
  dom.btnQuickUsuario?.addEventListener("click", () => ejecutarLogin("cliente1@gmail.com", "Cliente123!"));
  dom.btnQuickInvitado?.addEventListener("click", () => {
    loginModal?.hide();
    activarPestana("ADMIN");
    administracionManager.renderPorRol(null, null);
  });
}

async function ejecutarLogin(correo, password) {
  dom.loginErrorAlert?.classList.add("d-none");
  try {
    const res = await apiService.login(correo, password);
    currentUser = res.usuario;
    loginModal?.hide();
    dom.formLogin?.reset();
    await aplicarContextoUsuario();
  } catch (err) {
    if (dom.loginErrorAlert) {
      dom.loginErrorAlert.textContent = err.message;
      dom.loginErrorAlert.classList.remove("d-none");
    }
  }
}

async function restaurarSesion() {
  if (!apiService.getToken()) {
    currentUser = null;
    actualizarHeaderSesion();
    // Sin sesión: llevar directo al Catálogo Público / Acceso
    activarPestana("ADMIN");
    await administracionManager.renderPorRol(null, null);
    return;
  }

  try {
    const me = await apiService.getMe();
    currentUser = me;
    if (me.rol === "INVITADO" && me.sesion_invitado) {
      iniciarTimerInvitado(me.sesion_invitado);
      await cambiarVehiculoActivo(me.sesion_invitado.id_vehiculo, `Unidad Exhibición #${me.sesion_invitado.id_vehiculo}`);
      actualizarHeaderSesion();
      activarPestana("CONTROL");
      return;
    }
    await aplicarContextoUsuario();
  } catch {
    apiService.clearSession();
    currentUser = null;
    actualizarHeaderSesion();
    activarPestana("ADMIN");
    await administracionManager.renderPorRol(null, null);
  }
}

async function aplicarContextoUsuario() {
  actualizarHeaderSesion();
  if (!currentUser) return;

  if (currentUser.rol === "ADMIN" || currentUser.rol === "USUARIO") {
    try {
      const unidades = await apiService.getMisVehiculos();
      poblarSelectorHeader(unidades);
      if (unidades.length > 0) {
        await cambiarVehiculoActivo(unidades[0].id_vehiculo, unidades[0].nombre);
      } else {
        wsService.disconnect();
      }
    } catch (err) {
      console.warn("Error cargando unidades del usuario:", err);
    }

    if (currentUser.rol === "ADMIN") {
      activarPestana("ADMIN");
      await administracionManager.renderPorRol(currentUser, activeVehicleId);
    } else {
      activarPestana("CONTROL");
    }
  }
}

function poblarSelectorHeader(unidades) {
  if (!dom.headerVehiculoSelect) return;
  if (!unidades || unidades.length === 0) {
    dom.headerVehiculoSelect.classList.add("d-none");
    return;
  }
  dom.headerVehiculoSelect.innerHTML = unidades
    .map((u) => `<option value="${u.id_vehiculo}">#${u.id_vehiculo} · ${u.nombre}</option>`)
    .join("");
  dom.headerVehiculoSelect.classList.remove("d-none");
}

function actualizarHeaderSesion() {
  const rol = currentUser?.rol || null;
  dom.alertaSinSesion?.classList.toggle("d-none", Boolean(currentUser));

  if (!currentUser) {
    if (dom.authUserBadge) {
      dom.authUserBadge.className = "badge bg-secondary";
      dom.authUserBadge.innerHTML = '<i class="bi bi-person"></i> Sin sesión';
    }
    if (dom.btnAuthAction) {
      dom.btnAuthAction.className = "btn btn-sm btn-outline-info d-flex align-items-center gap-1";
      dom.btnAuthAction.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> <span>Iniciar Sesión</span>';
    }
    if (dom.tabLabelAdmin) dom.tabLabelAdmin.textContent = "Catálogo / Acceso";
    dom.headerVehiculoSelect?.classList.add("d-none");
    aplicarRestriccionesControles(null);
    return;
  }

  const badgeClass = rol === "ADMIN" ? "bg-danger" : rol === "USUARIO" ? "bg-primary" : "bg-info text-dark";
  if (dom.authUserBadge) {
    dom.authUserBadge.className = `badge ${badgeClass}`;
    dom.authUserBadge.innerHTML = `<i class="bi bi-person-badge me-1"></i>${rol}: ${currentUser.nombre_completo}`;
  }
  if (dom.btnAuthAction) {
    dom.btnAuthAction.className = "btn btn-sm btn-outline-danger d-flex align-items-center gap-1";
    dom.btnAuthAction.innerHTML = '<i class="bi bi-box-arrow-right"></i> <span>Salir</span>';
  }
  if (dom.tabLabelAdmin) {
    dom.tabLabelAdmin.textContent = rol === "ADMIN" ? "Administración" : rol === "USUARIO" ? "Mis Vehículos" : "Catálogo";
  }

  aplicarRestriccionesControles(rol);
}

function aplicarRestriccionesControles(rol) {
  const esInvitado = rol === "INVITADO";
  if (dom.btnSubir) dom.btnSubir.disabled = esInvitado;
  if (dom.btnBajar) dom.btnBajar.disabled = esInvitado;
  if (dom.btnGrabar) dom.btnGrabar.disabled = esInvitado;
  if (dom.cardDemoControl) dom.cardDemoControl.classList.toggle("d-none", esInvitado);
}

async function cambiarVehiculoActivo(vehicleId, vehicleName) {
  activeVehicleId = Number(vehicleId);
  activeVehicleName = vehicleName || `Unidad #${activeVehicleId}`;

  if (dom.vehiculoNombre) dom.vehiculoNombre.textContent = activeVehicleName;
  if (dom.headerVehiculoBadge) dom.headerVehiculoBadge.innerHTML = `<i class="bi bi-cpu"></i> Unidad #${activeVehicleId}`;
  if (dom.headerVehiculoSelect) dom.headerVehiculoSelect.value = String(activeVehicleId);

  // Actualizar Monitoreo y reconectar WSS autenticado solo a esta unidad
  monitoreoManager.setVehicle(activeVehicleId, activeVehicleName);
  wsService.connect(activeVehicleId, apiService.getToken());

  await Promise.all([
    monitoreoManager.cargarDatosCompletos().catch(() => null),
    adaptarBotonesPorCapacidad(activeVehicleId),
    currentUser?.rol !== "INVITADO" ? cargarDemosVehiculo(activeVehicleId) : Promise.resolve(),
  ]);
}

async function adaptarBotonesPorCapacidad(vehicleId) {
  if (currentUser?.rol === "INVITADO") {
    aplicarRestriccionesControles("INVITADO");
    return;
  }
  try {
    const cmds = await apiService.getComandos(vehicleId);
    const codigosActivos = new Set((cmds || []).filter((c) => c.activo).map((c) => Number(c.codigo)));
    if (codigosActivos.size > 0) {
      if (dom.btnSubir) dom.btnSubir.disabled = !codigosActivos.has(5);
      if (dom.btnBajar) dom.btnBajar.disabled = !codigosActivos.has(6);
      if (dom.btnLuz) dom.btnLuz.disabled = !codigosActivos.has(7);
      if (dom.btnGrabar) dom.btnGrabar.disabled = !codigosActivos.has(8);
    }
  } catch {
    // conservar estado actual
  }
}

async function cargarDemosVehiculo(vehicleId) {
  if (!dom.selectDemo || !apiService.getToken()) return;
  try {
    const demos = await apiService.getDemos(vehicleId);
    if (demos && demos.length > 0) {
      dom.selectDemo.innerHTML = demos.map((d) => `<option value="${d.id_demo}">${d.nombre}</option>`).join("");
    } else {
      dom.selectDemo.innerHTML = `<option value="">Sin DEMOs en esta unidad</option>`;
    }
  } catch {
    dom.selectDemo.innerHTML = `<option value="">Sin acceso a DEMOs</option>`;
  }
}

function iniciarTimerInvitado(sesion) {
  detenerTimerInvitado();
  guestSecondsLeft = Number(sesion.segundos_restantes ?? sesion.duracion_segundos ?? 90);
  dom.bannerInvitado?.classList.remove("d-none");
  if (dom.bannerInvitadoTexto) dom.bannerInvitadoTexto.textContent = `Unidad #${sesion.id_vehiculo}`;
  if (dom.bannerInvitadoTimer) dom.bannerInvitadoTimer.textContent = `${guestSecondsLeft}s`;

  guestTimerInterval = setInterval(async () => {
    guestSecondsLeft -= 1;
    if (dom.bannerInvitadoTimer) dom.bannerInvitadoTimer.textContent = `${Math.max(0, guestSecondsLeft)}s`;
    if (guestSecondsLeft <= 0) {
      await finalizarModoInvitado(true);
    }
  }, 1000);
}

function detenerTimerInvitado() {
  if (guestTimerInterval) {
    clearInterval(guestTimerInterval);
    guestTimerInterval = null;
  }
  dom.bannerInvitado?.classList.add("d-none");
}

async function finalizarModoInvitado(expirada = false) {
  detenerTimerInvitado();
  wsService.disconnect();
  try {
    await apiService.finalizarSesionInvitado();
  } catch {
    apiService.clearSession();
  }
  currentUser = null;
  actualizarHeaderSesion();
  activarPestana("ADMIN");
  await administracionManager.renderPorRol(null, null);
  administracionManager.showFeedback(
    expirada ? "Tu sesión de exhibición expiró y el vehículo se detuvo automáticamente." : "Sesión de exhibición finalizada y reserva liberada.",
    "info"
  );
}

async function cerrarSesionActual() {
  detenerTimerInvitado();
  wsService.disconnect();
  await apiService.logout();
  currentUser = null;
  actualizarHeaderSesion();
  activarPestana("ADMIN");
  await administracionManager.renderPorRol(null, null);
}

// 4. Joystick y Botones (4.1)
function initJoystick() {
  new VirtualJoystick(dom.joystickContainer, (direction) => {
    dom.joystickDirectionText.textContent = direction;
    const codigoComando = COMANDO_MAP[direction];
    if (codigoComando) {
      ejecutarComando(codigoComando, `JOYSTICK_${direction}`);
    }
  });
}

function bindButtons() {
  dom.btnDetener.addEventListener("click", () => {
    ejecutarComando(COMANDO_MAP.DETENER, "BOTON_DETENER_PRIORITARIO");
    if (appState.demoActiva) {
      apiService.cancelarDemo(activeVehicleId).catch(() => {});
    }
  });

  dom.btnSubir.addEventListener("click", () => ejecutarComando(COMANDO_MAP.SUBIR, "BOTON_SUBIR"));
  dom.btnBajar.addEventListener("click", () => ejecutarComando(COMANDO_MAP.BAJAR, "BOTON_BAJAR"));
  dom.btnLuz.addEventListener("click", () => ejecutarComando(COMANDO_MAP.LUZ, "BOTON_LUZ"));
  dom.btnGrabar.addEventListener("click", () => ejecutarComando(COMANDO_MAP.GRABAR, "BOTON_GRABAR_MEMORIA"));

  dom.btnIniciarDemo.addEventListener("click", async () => {
    const idDemo = dom.selectDemo.value;
    if (!idDemo) return;
    try {
      dom.btnIniciarDemo.disabled = true;
      dom.btnCancelarDemo.disabled = false;
      actualizarLog("DEMO Iniciar", "Enviando...", "Esperando WSS...");
      await apiService.iniciarDemo(idDemo, activeVehicleId);
      appState.demoActiva = true;
      actualizarLog(`DEMO Iniciar (#${idDemo})`, "202 Aceptada", "WSS notificará pasos");
    } catch (err) {
      actualizarLog("DEMO Error", `Fallo: ${err.message}`, "Sin evento");
      dom.btnIniciarDemo.disabled = false;
      dom.btnCancelarDemo.disabled = true;
    }
  });

  dom.btnCancelarDemo.addEventListener("click", async () => {
    try {
      await apiService.cancelarDemo(activeVehicleId);
      ejecutarComando(COMANDO_MAP.DETENER, "CANCELAR_DEMO");
      actualizarLog("DEMO Cancelar", "200 Enviada", "Cancelando...");
    } catch (err) {
      actualizarLog("DEMO Cancelar", `Error: ${err.message}`, "-");
    }
  });
}

let ultimoComandoTs = 0;

async function ejecutarComando(codigo, origen = "FRONTEND-WEB") {
  if (!apiService.getToken()) {
    actualizarLog(`Comando ${codigo}`, "401 Sin sesión", "Inicia sesión");
    loginModal?.show();
    return;
  }

  const esDetener = codigo === 9 || codigo === COMANDO_MAP.DETENER;
  const ahora = Date.now();

  // Throttling de 120ms para giros/movimientos repetidos de joystick
  // DETENER (9) NUNCA se restringe; pasa con prioridad máxima inmediata
  if (!esDetener && ahora - ultimoComandoTs < 120) {
    return;
  }
  ultimoComandoTs = ahora;

  appState.ultimaAccion.solicitada = `Comando ${codigo} (${origen})`;
  actualizarLog(`U#${activeVehicleId} Cmd ${codigo}`, "Enviando...", "Pendiente WSS...");

  try {
    const res = await apiService.enviarMovimiento(codigo, activeVehicleId, origen);
    actualizarLog(
      `U#${activeVehicleId} [${res.comando || "OK"}]`,
      "HTTP 200 Aceptado",
      appState.ultimaAccion.eventoWs || "WSS Activo"
    );
  } catch (err) {
    actualizarLog(`U#${activeVehicleId} Cmd ${codigo}`, `Error ${err.status || ""}: ${err.message}`, "Rechazado");
  }
}

// 5. WebSocket Compartido
function initWebSocketListeners() {
  wsService.onStateChange((state) => {
    appState.wsEstado = state;
    renderWsStatus(state);
    if (state === WsState.ONLINE && apiService.getToken()) {
      monitoreoManager.cargarDatosCompletos().catch(() => {});
    }
  });

  wsService.onMessage((msg) => {
    handleWebSocketMessage(msg);
  });
}

function handleWebSocketMessage(msg) {
  if (msg.id_vehiculo && Number(msg.id_vehiculo) !== Number(activeVehicleId)) return;

  const evento = msg.evento || "EVENTO_RECIBIDO";
  const cmd = msg.comando || msg.codigo || "-";
  appState.ultimaAccion.eventoWs = `${evento}: ${cmd}`;

  dom.logWs.textContent = `${evento} (${cmd})`;
  dom.logWs.className = "badge bg-success-subtle text-success border border-success-subtle";

  monitoreoManager.procesarEventoWss(msg);

  if (evento === "SESION_INVITADO_EXPIRADA" && currentUser?.rol === "INVITADO") {
    finalizarModoInvitado(true);
    return;
  }

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

// 6. Health Polling (/health)
function initHealthPolling() {
  const check = async () => {
    try {
      const data = await apiService.getHealth();
      renderApiStatus(data.api === "ok" ? "DISPONIBLE" : "NO_DISPONIBLE");
      renderRdsStatus(data.base_de_datos === "ok" ? "DISPONIBLE" : "NO_DISPONIBLE");
    } catch {
      renderApiStatus("NO_DISPONIBLE");
      renderRdsStatus("SIN_VERIFICAR");
    }
  };
  check();
  setInterval(check, CONFIG.HEALTH_CHECK_INTERVAL_MS);
}

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
