/**
 * monitoreo.js - Componente modular para la vista de MONITOREO IoT en tiempo real (4.2 + 4.3)
 * - Filtra estrictamente eventos WSS por el id_vehiculo activo (evita fugas entre unidades).
 * - Actualiza tarjeta de último movimiento en vivo y sincroniza los 10 registros persistidos en RDS.
 * - Regla estricta: MOVIMIENTO_DEMO actualiza la tarjeta en vivo pero NO contamina la tabla individual.
 */

import { apiService } from "../services/apiService.js?v=20261123c";

export function formatearFechaHora(fechaStr) {
  if (!fechaStr) return { fecha: "--", hora: "--" };
  try {
    const d = new Date(fechaStr);
    if (isNaN(d.getTime())) return { fecha: fechaStr, hora: "" };
    const fecha = d.toLocaleDateString("es-MX", { year: "numeric", month: "2-digit", day: "2-digit" });
    const hora = d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
    return { fecha, hora };
  } catch {
    return { fecha: fechaStr, hora: "" };
  }
}

export function getBadgeComando(nombre, codigo) {
  const c = String(nombre || "").toUpperCase();
  let bgClass = "bg-secondary";
  let icon = "bi-gear";

  if (c.includes("AVANZAR")) { bgClass = "bg-primary"; icon = "bi-arrow-up-circle"; }
  else if (c.includes("RETROCEDER")) { bgClass = "bg-info text-dark"; icon = "bi-arrow-down-circle"; }
  else if (c.includes("IZQUIERDA")) { bgClass = "bg-primary-subtle text-primary border border-primary-subtle"; icon = "bi-arrow-left-circle"; }
  else if (c.includes("DERECHA")) { bgClass = "bg-primary-subtle text-primary border border-primary-subtle"; icon = "bi-arrow-right-circle"; }
  else if (c.includes("SUBIR")) { bgClass = "bg-info"; icon = "bi-chevron-double-up"; }
  else if (c.includes("BAJAR")) { bgClass = "bg-info"; icon = "bi-chevron-double-down"; }
  else if (c.includes("LUZ")) { bgClass = "bg-warning text-dark"; icon = "bi-lightbulb-fill"; }
  else if (c.includes("DETENER")) { bgClass = "bg-danger"; icon = "bi-stop-circle-fill"; }
  else if (c.includes("DEMO") || c.includes("GRABAR")) { bgClass = "bg-success"; icon = "bi-play-circle"; }

  const codText = codigo !== undefined && codigo !== null ? ` (#${codigo})` : "";
  return `<span class="badge ${bgClass}"><i class="bi ${icon} me-1"></i>${c}${codText}</span>`;
}

class MonitoreoManager {
  constructor() {
    this.vehicleId = 1;
    this.vehicleName = "Excavadora IoT";
    this.ultimoEstado = null;
    this.historial = [];
    this.syncTimeout = null;
    this.cargando = false;

    this.dom = {
      cardTituloVehiculo: document.getElementById("monitoreoTituloVehiculo"),
      cardComando: document.getElementById("monitoreoUltimoComando"),
      cardBadge: document.getElementById("monitoreoUltimoBadge"),
      cardFecha: document.getElementById("monitoreoUltimaFecha"),
      cardHora: document.getElementById("monitoreoUltimaHora"),
      cardOrigen: document.getElementById("monitoreoUltimoOrigen"),
      tablaBody: document.getElementById("tablaHistorialBody"),
      tablaEstadoText: document.getElementById("tablaEstadoText"),
      btnRefrescar: document.getElementById("btnRefrescarMonitoreo"),
    };

    if (this.dom.btnRefrescar) {
      this.dom.btnRefrescar.addEventListener("click", () => this.cargarDatosCompletos());
    }
  }

  setVehicle(vehicleId, vehicleName = null) {
    this.vehicleId = Number(vehicleId);
    if (vehicleName) this.vehicleName = vehicleName;
    if (this.dom.cardTituloVehiculo) {
      this.dom.cardTituloVehiculo.textContent = `Vehículo #${this.vehicleId} · ${this.vehicleName}`;
    }
    this.ultimoEstado = null;
    this.historial = [];
  }

  async cargarDatosCompletos() {
    if (!apiService.getToken() || !this.vehicleId) {
      if (this.dom.tablaBody) {
        this.dom.tablaBody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center py-4 text-secondary">
              <i class="bi bi-lock fs-4 d-block mb-1"></i>
              Inicia sesión o reserva una unidad de exhibición para monitorear telemetría.
            </td>
          </tr>`;
      }
      return;
    }

    this.cargando = true;
    this._renderCargando(true);
    const targetId = this.vehicleId;

    try {
      const [estadoData, historialData] = await Promise.all([
        apiService.getEstado(targetId),
        apiService.getHistorial(targetId),
      ]);

      // Protección contra respuestas atrasadas si el usuario cambió de vehículo
      if (targetId !== this.vehicleId) return;

      if (estadoData && (estadoData.comando || estadoData.id_comando)) {
        this.renderTarjetaUltimoEstado({
          comando: estadoData.comando || `Comando #${estadoData.id_comando}`,
          codigo: estadoData.codigo ?? estadoData.id_comando,
          fecha_actualizacion: estadoData.fecha_actualizacion,
          origen: "PERSISTIDO EN RDS",
        });
      } else {
        this.renderTarjetaUltimoEstado({
          comando: "SIN MOVIMIENTOS",
          codigo: null,
          fecha_actualizacion: null,
          origen: "RDS",
        });
      }

      this.historial = Array.isArray(historialData) ? historialData.slice(0, 10) : [];
      if (this.dom.tablaEstadoText) {
        this.dom.tablaEstadoText.textContent = `Registros persistidos en Amazon RDS · Unidad #${this.vehicleId}`;
      }
      this.renderTablaHistorial();
    } catch (err) {
      if (this.dom.tablaEstadoText) {
        this.dom.tablaEstadoText.textContent = `Error: ${err.message}`;
      }
      if (this.dom.tablaBody) {
        this.dom.tablaBody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center py-4 text-danger">
              <i class="bi bi-shield-exclamation fs-4 d-block mb-1"></i>
              ${err.message}
            </td>
          </tr>`;
      }
    } finally {
      this.cargando = false;
      this._renderCargando(false);
    }
  }

  renderTarjetaUltimoEstado(datos) {
    if (!datos) return;
    this.ultimoEstado = datos;

    const nombre = datos.comando || "DETENER";
    const codigo = datos.codigo !== undefined ? datos.codigo : datos.id_comando;
    const { fecha, hora } = formatearFechaHora(datos.fecha_actualizacion || datos.timestamp);

    if (this.dom.cardComando) this.dom.cardComando.textContent = nombre;
    if (this.dom.cardBadge) this.dom.cardBadge.innerHTML = getBadgeComando(nombre, codigo);
    if (this.dom.cardFecha) this.dom.cardFecha.textContent = fecha;
    if (this.dom.cardHora) this.dom.cardHora.textContent = hora;
    if (this.dom.cardOrigen) this.dom.cardOrigen.textContent = datos.origen || "EN VIVO (WSS)";
  }

  renderTablaHistorial() {
    if (!this.dom.tablaBody) return;

    if (!this.historial || this.historial.length === 0) {
      this.dom.tablaBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-4 text-secondary">
            <i class="bi bi-inbox fs-4 d-block mb-1"></i>
            Sin movimientos registrados para esta unidad
          </td>
        </tr>`;
      return;
    }

    this.dom.tablaBody.innerHTML = this.historial
      .map((item, index) => {
        const { fecha, hora } = formatearFechaHora(item.fecha_hora);
        const badge = getBadgeComando(item.comando, item.codigo);
        const origen = item.origen || "API";
        return `
          <tr>
            <td class="text-secondary fw-semibold">${index + 1}</td>
            <td>${badge}</td>
            <td><span class="text-white">${fecha}</span></td>
            <td><span class="text-info">${hora}</span></td>
            <td><small class="badge bg-dark border border-secondary text-secondary">${origen}</small></td>
          </tr>`;
      })
      .join("");
  }

  procesarEventoWss(msg) {
    if (!msg || !msg.evento) return;
    // Filtrar estrictamente eventos de otros vehículos
    if (msg.id_vehiculo && Number(msg.id_vehiculo) !== Number(this.vehicleId)) return;

    if (msg.evento === "MOVIMIENTO_INDIVIDUAL") {
      this.renderTarjetaUltimoEstado({
        comando: msg.comando,
        codigo: msg.codigo,
        timestamp: msg.timestamp || new Date().toISOString(),
        origen: msg.origen || "WSS EN TIEMPO REAL",
      });
      this._solicitarSyncHistorial();
    } else if (msg.evento === "MOVIMIENTO_DEMO") {
      // Regla estricta: DEMO actualiza tarjeta pero NO entra al historial individual
      this.renderTarjetaUltimoEstado({
        comando: msg.comando,
        codigo: msg.codigo,
        timestamp: msg.timestamp || new Date().toISOString(),
        origen: `DEMO (Paso ${msg.orden || "-"})`,
      });
    } else if (msg.evento === "DEMO_FINALIZADA" || msg.evento === "DEMO_CANCELADA") {
      this.renderTarjetaUltimoEstado({
        comando: "DETENER",
        codigo: 9,
        timestamp: msg.timestamp || new Date().toISOString(),
        origen: msg.evento === "DEMO_FINALIZADA" ? "FIN DE DEMO" : "DEMO CANCELADA",
      });
    } else if (msg.evento === "CONEXION_ESTABLECIDA" && msg.estado) {
      this.renderTarjetaUltimoEstado({
        comando: msg.estado.comando,
        codigo: msg.estado.codigo ?? msg.estado.id_comando,
        fecha_actualizacion: msg.estado.fecha_actualizacion,
        origen: "ESTADO INICIAL",
      });
    }
  }

  _solicitarSyncHistorial() {
    if (this.syncTimeout) clearTimeout(this.syncTimeout);
    const targetId = this.vehicleId;
    this.syncTimeout = setTimeout(async () => {
      if (targetId !== this.vehicleId || !apiService.getToken()) return;
      try {
        const data = await apiService.getHistorial(targetId);
        if (Array.isArray(data) && targetId === this.vehicleId) {
          this.historial = data.slice(0, 10);
          this.renderTablaHistorial();
        }
      } catch (err) {
        console.warn("Fallo al resincronizar historial tras WSS:", err);
      }
    }, 450);
  }

  _renderCargando(cargando) {
    if (this.dom.btnRefrescar) {
      this.dom.btnRefrescar.disabled = cargando;
      this.dom.btnRefrescar.innerHTML = cargando
        ? '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Cargando...'
        : '<i class="bi bi-arrow-clockwise me-1"></i> Refrescar';
    }
  }
}

export const monitoreoManager = new MonitoreoManager();
