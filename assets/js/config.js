/**
 * config.js - Configuración centralizada de endpoints y URLs de AWS
 * Compatible con GitHub Pages (sin secretos incrustados)
 */

export const CONFIG = {
  // URL base HTTPS con certificado SSL oficial de confianza mundial (Cloudflare)
  API_BASE_URL: "https://bath-sunrise-stomach-grown.trycloudflare.com",

  // URL WebSocket WSS segura
  WS_URL: "wss://bath-sunrise-stomach-grown.trycloudflare.com/ws/vehiculo/1",

  // ID del vehículo asignado para la práctica
  VEHICLE_ID: 1,

  // Rutas y contratos de endpoints
  ENDPOINTS: {
    HEALTH: "/health",
    VEHICULO: (id) => `/vehiculos/${id}`,
    COMANDOS: (id) => `/comandos/vehiculo/${id}`,
    MOVIMIENTO: (id) => `/vehiculos/${id}/movimiento`,
    DEMOS: (id) => `/vehiculos/${id}/demos`,
    INICIAR_DEMO: (idVehiculo, idDemo) => `/vehiculos/${idVehiculo}/demos/${idDemo}/iniciar`,
    CANCELAR_DEMO: (idVehiculo) => `/vehiculos/${idVehiculo}/demos/cancelar`,
  },

  // Parámetros de monitoreo periódico
  HEALTH_CHECK_INTERVAL_MS: 5000,
  WS_RECONNECT_INTERVAL_MS: 3000,
  REQUEST_TIMEOUT_MS: 6000,
};

