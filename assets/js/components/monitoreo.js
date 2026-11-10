/**
 * monitoreo.js - Componente modular para la vista de MONITOREO IoT en tiempo real
 * Cumple con:
 * 1. Tarjeta visual destacada del último movimiento/estado reportado.
 * 2. Tabla semántica responsiva de los últimos 10 movimientos individuales (RDS).
 * 3. Actualización inmediata por WSS sin recargar la página.
 * 4. Regla estricta: los movimientos de DEMO actualizan el estado en vivo,
 *    pero NO contaminan la tabla de historial individual.
 */

import { apiService } from "../services/apiService.js";

// Utilidad para formatear fechas de forma segura y legible
export function formatearFechaHora(fechaStr) {
  if (!fechaStr) return { fecha: "--", hora: "--" };
  try {
    const d = new Date(fechaStr);
    if (isNaN(d.getTime())) return { fecha: fechaStr, hora: "" };
    
    const fecha = d.toLocaleDateString("es-MX", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    const hora = d.toLocaleTimeString("es-MX", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    return { fecha, hora };
  } catch {
    return { fecha: fechaStr, hora: "" };
  }
}

// Genera un badge de color según el comando
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

  const codText = (codigo !== undefined && codigo !== null) ? ` (#${codigo})` : "";
  return `<span class="badge ${bgClass}"><i class="bi ${icon} me-1"></i>${c}${codText}</span>`;
}

class MonitoreoManager {
  constructor() {
    this.ultimoEstado = null;
    this.historial = [];
    this.syncTimeout = null;
    this.cargando = false;

    // Elementos DOM de Monitoreo
    this.dom = {
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

  // 1. Carga inicial vía REST de estado e historial (10 más recientes)
  async cargarDatosCompletos() {
    this.cargando = true;
    this._renderCargando(true);

    try {
      const [estadoData, historialData] = await Promise.all([
        apiService.getEstado().catch(() => null),
        apiService.getHistorial().catch(() => []),
      ]);

      if (estadoData && (estadoData.comando || estadoData.id_comando)) {
        this.renderTarjetaUltimoEstado({
          comando: estadoData.comando || `Comando #${estadoData.id_comando}`,
          codigo: estadoData.codigo || estadoData.id_comando,
          fecha_actualizacion: estadoData.fecha_actualizacion,
          origen: "PERSISTIDO EN RDS",
        });
      }

      this.historial = Array.isArray(historialData) ? historialData.slice(0, 10) : [];
      this.renderTablaHistorial();
    } catch (err) {
      console.error("Error al cargar datos de monitoreo:", err);
      if (this.dom.tablaEstadoText) {
        this.dom.tablaEstadoText.textContent = "Error de conexión al consultar RDS";
      }
    } finally {
      this.cargando = false;
      this._renderCargando(false);
    }
  }

  // 2. Renderizado de la Tarjeta Destacada de Último Movimiento
  renderTarjetaUltimoEstado(datos) {
    if (!datos) return;
    this.ultimoEstado = datos;

    const nombre = datos.comando || "DETENER";
    const codigo = datos.codigo !== undefined ? datos.codigo : datos.id_comando;
    const { fecha, hora } = formatearFechaHora(datos.fecha_actualizacion || datos.timestamp || new Date().toISOString());

    if (this.dom.cardComando) this.dom.cardComando.textContent = nombre;
    if (this.dom.cardBadge) this.dom.cardBadge.innerHTML = getBadgeComando(nombre, codigo);
    if (this.dom.cardFecha) this.dom.cardFecha.textContent = fecha;
    if (this.dom.cardHora) this.dom.cardHora.textContent = hora;
    if (this.dom.cardOrigen) this.dom.cardOrigen.textContent = datos.origen || "EN VIVO (WSS)";
  }

  // 3. Renderizado de la Tabla Semántica de los 10 Movimientos
  renderTablaHistorial() {
    if (!this.dom.tablaBody) return;

    if (!this.historial || this.historial.length === 0) {
      this.dom.tablaBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-4 text-secondary">
            <i class="bi bi-inbox fs-4 d-block mb-1"></i>
            Sin movimientos registrados en el historial
          </td>
        </tr>`;
      return;
    }

    const html = this.historial.map((item, index) => {
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
    }).join("");

    this.dom.tablaBody.innerHTML = html;
  }

  // 4. Recepción de Eventos WebSocket en Vivo
  procesarEventoWss(msg) {
    if (!msg || !msg.evento) return;

    // Caso A: Movimiento individual confirmado en WSS
    if (msg.evento === "MOVIMIENTO_INDIVIDUAL") {
      this.renderTarjetaUltimoEstado({
        comando: msg.comando,
        codigo: msg.codigo,
        timestamp: msg.timestamp || new Date().toISOString(),
        origen: msg.origen || "WSS EN TIEMPO REAL",
      });

      // Disparar sincronización controlada con RDS para traer el registro recién persistido
      this._solicitarSyncHistorial();
    }

    // Caso B: Pasos de DEMO en ejecución
    // La regla de negocio dice: la tarjeta de estado se actualiza en tiempo real,
    // pero la tabla de historial NO se contamina con pasos internos de DEMO.
    else if (msg.evento === "MOVIMIENTO_DEMO") {
      this.renderTarjetaUltimoEstado({
        comando: msg.comando,
        codigo: msg.codigo,
        timestamp: msg.timestamp || new Date().toISOString(),
        origen: `DEMO (Paso ${msg.orden || "-"})`,
      });
    }

    // Caso C: DEMO finalizada o cancelada
    else if (msg.evento === "DEMO_FINALIZADA" || msg.evento === "DEMO_CANCELADA") {
      this.renderTarjetaUltimoEstado({
        comando: "DETENER",
        codigo: 9,
        timestamp: msg.timestamp || new Date().toISOString(),
        origen: msg.evento === "DEMO_FINALIZADA" ? "FIN DE DEMO" : "DEMO CANCELADA",
      });
    }

    // Caso D: Conexión establecida con estado inicial
    else if (msg.evento === "CONEXION_ESTABLECIDA" && msg.estado) {
      this.renderTarjetaUltimoEstado({
        comando: msg.estado.comando,
        codigo: msg.estado.codigo || msg.estado.id_comando,
        fecha_actualizacion: msg.estado.fecha_actualizacion,
        origen: "ESTADO INICIAL",
      });
    }
  }

  // Sincronización controlada antirráfagas (Debounce)
  _solicitarSyncHistorial() {
    if (this.syncTimeout) clearTimeout(this.syncTimeout);
    this.syncTimeout = setTimeout(async () => {
      try {
        const data = await apiService.getHistorial();
        if (Array.isArray(data)) {
          this.historial = data.slice(0, 10);
          this.renderTablaHistorial();
        }
      } catch (err) {
        console.warn("Fallo al resincronizar historial tras WSS:", err);
      }
    }, 450); // 450ms de tolerancia para asegurar commit en RDS
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
