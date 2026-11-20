/**
 * apiService.js - Cliente HTTP modular con Fetch, async/await, Bearer JWT y timeout seguro.
 * Usa sessionStorage para permitir pruebas multi-pestaña (Admin, Usuario e Invitado en paralelo).
 */

import { CONFIG } from "../config.js?v=20261119b";

const TOKEN_KEY = "iot_43_jwt_token";
const USER_KEY = "iot_43_user_profile";

class ApiService {
  constructor() {
    this.baseUrl = CONFIG.API_BASE_URL;
  }

  getToken() {
    return sessionStorage.getItem(TOKEN_KEY) || null;
  }

  setSession(token, user) {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  getStoredUser() {
    try {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  clearSession() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  }

  async _request(endpoint, options = {}, { auth = true } = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT_MS);

    const headers = {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    const token = this.getToken();
    if (auth && token) {
      headers.Authorization = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorDetail = data?.detail || `Error HTTP ${response.status}`;
        const err = new Error(errorDetail);
        err.status = response.status;
        throw err;
      }

      return data;
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        throw new Error("Tiempo de espera agotado (Timeout)");
      }
      throw err;
    }
  }

  // ==================== 4.1 & 4.2 ====================
  async getHealth() { return this._request(CONFIG.ENDPOINTS.HEALTH, {}, { auth: false }); }
  async getVehiculo(id = CONFIG.VEHICLE_ID) { return this._request(CONFIG.ENDPOINTS.VEHICULO(id)); }
  async getComandos(id = CONFIG.VEHICLE_ID) { return this._request(CONFIG.ENDPOINTS.COMANDOS(id)); }
  async getEstado(id = CONFIG.VEHICLE_ID) { return this._request(CONFIG.ENDPOINTS.ESTADO(id)); }
  async getHistorial(id = CONFIG.VEHICLE_ID) { return this._request(CONFIG.ENDPOINTS.HISTORIAL(id)); }
  async getDemos(id = CONFIG.VEHICLE_ID) { return this._request(CONFIG.ENDPOINTS.DEMOS(id)); }

  async enviarMovimiento(comando, id = CONFIG.VEHICLE_ID, origen = "FRONTEND-WEB") {
    return this._request(CONFIG.ENDPOINTS.MOVIMIENTO(id), {
      method: "POST",
      body: JSON.stringify({ comando, origen }),
    });
  }

  async iniciarDemo(idDemo, idVehiculo = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.INICIAR_DEMO(idVehiculo, idDemo), { method: "POST" });
  }

  async cancelarDemo(idVehiculo = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.CANCELAR_DEMO(idVehiculo), { method: "POST" });
  }

  // ==================== 4.3 AUTENTICACIÓN ====================
  async login(correo, password) {
    const res = await this._request(
      CONFIG.ENDPOINTS.LOGIN,
      { method: "POST", body: JSON.stringify({ correo, password }) },
      { auth: false }
    );
    this.setSession(res.access_token, res.usuario);
    return res;
  }

  async logout() {
    try {
      if (this.getToken()) {
        await this._request(CONFIG.ENDPOINTS.LOGOUT, { method: "POST" });
      }
    } finally {
      this.clearSession();
    }
  }

  async getMe() {
    return this._request(CONFIG.ENDPOINTS.ME);
  }

  // ==================== 4.3 ADMINISTRACIÓN ====================
  async getDashboard() { return this._request(CONFIG.ENDPOINTS.ADMIN_DASHBOARD); }
  async getModelos() { return this._request(CONFIG.ENDPOINTS.ADMIN_MODELOS); }
  async crearModelo(payload) { return this._request(CONFIG.ENDPOINTS.ADMIN_MODELOS, { method: "POST", body: JSON.stringify(payload) }); }
  async getUnidadesAdmin() { return this._request(CONFIG.ENDPOINTS.ADMIN_UNIDADES); }
  async crearUnidad(payload) { return this._request(CONFIG.ENDPOINTS.ADMIN_UNIDADES, { method: "POST", body: JSON.stringify(payload) }); }
  async asignarUnidad(idVehiculo, payload) {
    return this._request(CONFIG.ENDPOINTS.ADMIN_ASIGNAR(idVehiculo), { method: "PATCH", body: JSON.stringify(payload) });
  }
  async bajaLogicaUnidad(idVehiculo) {
    return this._request(CONFIG.ENDPOINTS.ADMIN_UNIDAD(idVehiculo), { method: "DELETE" });
  }
  async getClientes() { return this._request(CONFIG.ENDPOINTS.ADMIN_CLIENTES); }
  async crearCliente(payload) { return this._request(CONFIG.ENDPOINTS.ADMIN_CLIENTES, { method: "POST", body: JSON.stringify(payload) }); }
  async getAuditoria(limit = 50) { return this._request(CONFIG.ENDPOINTS.ADMIN_AUDITORIA(limit)); }

  // ==================== 4.3 USUARIO (MIS VEHÍCULOS) ====================
  async getMisVehiculos() { return this._request(CONFIG.ENDPOINTS.MIS_VEHICULOS); }
  async autorizarSoporte(idVehiculo, autorizado) {
    return this._request(CONFIG.ENDPOINTS.AUTORIZAR_SOPORTE(idVehiculo), {
      method: "PATCH",
      body: JSON.stringify({ autorizado }),
    });
  }

  // ==================== 4.3 EDITOR DE DEMOS ====================
  async getDemosEditor(idVehiculo) { return this._request(CONFIG.ENDPOINTS.EDITOR_DEMOS_VEHICULO(idVehiculo)); }
  async crearDemoCompleta(payload) { return this._request(CONFIG.ENDPOINTS.EDITOR_DEMOS, { method: "POST", body: JSON.stringify(payload) }); }
  async editarDemoCompleta(idDemo, payload) { return this._request(CONFIG.ENDPOINTS.EDITOR_DEMO(idDemo), { method: "PUT", body: JSON.stringify(payload) }); }
  async eliminarDemoEditor(idDemo) { return this._request(CONFIG.ENDPOINTS.EDITOR_DEMO(idDemo), { method: "DELETE" }); }

  // ==================== 4.3 INVITADO Y CATÁLOGO ====================
  async getCatalogoPublico() { return this._request(CONFIG.ENDPOINTS.CATALOGO_PUBLICO, {}, { auth: false }); }
  async iniciarSesionInvitado(idVehiculo, nombreInvitado, duracionSegundos = 90) {
    const res = await this._request(
      CONFIG.ENDPOINTS.INVITADO_INICIAR,
      {
        method: "POST",
        body: JSON.stringify({
          id_vehiculo: idVehiculo,
          nombre_invitado: nombreInvitado,
          duracion_segundos: duracionSegundos,
        }),
      },
      { auth: false }
    );
    this.setSession(res.access_token, {
      id_usuario: null,
      nombre_completo: res.sesion.nombre_invitado,
      correo: "Modo Invitado (Exhibición)",
      rol: "INVITADO",
      sesion_invitado: res.sesion,
    });
    return res;
  }
  async finalizarSesionInvitado() {
    try {
      await this._request(CONFIG.ENDPOINTS.INVITADO_FINALIZAR, { method: "POST" });
    } finally {
      this.clearSession();
    }
  }
}

export const apiService = new ApiService();
