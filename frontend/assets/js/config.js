/**
 * config.js - Configuración centralizada de endpoints y URLs de AWS
 * Compatible con GitHub Pages (sin secretos incrustados)
 */

export const CONFIG = {
  // URL base HTTPS de la API en Amazon EC2
  API_BASE_URL: "https://44.194.225.196:8000",

  // URL WebSocket WSS del vehículo 1
  WS_URL: "wss://44.194.225.196:8000/ws/vehiculo/1",

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

