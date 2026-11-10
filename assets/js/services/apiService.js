/**
 * apiService.js - Cliente HTTP modular con Fetch, async/await y timeout seguro
 */

import { CONFIG } from "../config.js";

class ApiService {
  constructor() {
    this.baseUrl = CONFIG.API_BASE_URL;
  }

  async _request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT_MS);

    const defaultHeaders = {
      "Accept": "application/json",
      "Content-Type": "application/json",
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...defaultHeaders,
          ...options.headers,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorDetail = data?.detail || `Error HTTP ${response.status}`;
        throw new Error(errorDetail);
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

  // 1. Diagnóstico de salud seguro (API + RDS)
  async getHealth() {
    return this._request(CONFIG.ENDPOINTS.HEALTH);
  }

  // 2. Información del vehículo
  async getVehiculo(id = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.VEHICULO(id));
  }

  // 3. Catálogo de comandos del vehículo
  async getComandos(id = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.COMANDOS(id));
  }

  // 3.1 Último estado del vehículo (RDS)
  async getEstado(id = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.ESTADO(id));
  }

  // 3.2 Últimos 10 movimientos individuales (RDS)
  async getHistorial(id = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.HISTORIAL(id));
  }

  // 4. Catálogo de DEMOs disponibles
  async getDemos(id = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.DEMOS(id));
  }

  // 5. Ejecución de movimiento individual (POST)
  async enviarMovimiento(comando, id = CONFIG.VEHICLE_ID, origen = "FRONTEND-WEB") {
    return this._request(CONFIG.ENDPOINTS.MOVIMIENTO(id), {
      method: "POST",
      body: JSON.stringify({
        comando: comando,
        origen: origen,
      }),
    });
  }

  // 6. Iniciar DEMO seleccionada
  async iniciarDemo(idDemo, idVehiculo = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.INICIAR_DEMO(idVehiculo, idDemo), {
      method: "POST",
    });
  }

  // 7. Cancelar DEMO en ejecución
  async cancelarDemo(idVehiculo = CONFIG.VEHICLE_ID) {
    return this._request(CONFIG.ENDPOINTS.CANCELAR_DEMO(idVehiculo), {
      method: "POST",
    });
  }
}

export const apiService = new ApiService();

