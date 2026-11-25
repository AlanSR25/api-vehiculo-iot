/**
 * config.js - Configuración centralizada de endpoints y URLs de AWS (Prácticas 4.1, 4.2 y 4.3)
 * Compatible con GitHub Pages (sin secretos incrustados)
 */

const BASE_HOST = "platinum-nissan-orlando-proved.trycloudflare.com";

export const CONFIG = {
  // URL base HTTPS con certificado SSL oficial de confianza mundial (Cloudflare)
  API_BASE_URL: `https://${BASE_HOST}`,

  // URL WebSocket WSS segura (dinámica por vehículo y token JWT)
  WS_BASE_URL: `wss://${BASE_HOST}/ws/vehiculo`,
  WS_URL: `wss://${BASE_HOST}/ws/vehiculo/1`,

  // ID del vehículo por defecto
  VEHICLE_ID: 1,

  // Rutas y contratos de endpoints
  ENDPOINTS: {
    // 4.1 & 4.2
    HEALTH: "/health",
    VEHICULO: (id) => `/vehiculos/${id}`,
    COMANDOS: (id) => `/comandos/vehiculo/${id}`,
    ESTADO: (id) => `/vehiculos/${id}/estado`,
    HISTORIAL: (id) => `/vehiculos/${id}/historial`,
    MOVIMIENTO: (id) => `/vehiculos/${id}/movimiento`,
    DEMOS: (id) => `/vehiculos/${id}/demos`,
    INICIAR_DEMO: (idVehiculo, idDemo) => `/vehiculos/${idVehiculo}/demos/${idDemo}/iniciar`,
    CANCELAR_DEMO: (idVehiculo) => `/vehiculos/${idVehiculo}/demos/cancelar`,

    // 4.3 Autenticación
    LOGIN: "/auth/login",
    LOGOUT: "/auth/logout",
    ME: "/auth/me",

    // 4.3 Administración (Admin)
    ADMIN_DASHBOARD: "/admin/dashboard",
    ADMIN_MODELOS: "/admin/modelos",
    ADMIN_MODELO: (id) => `/admin/modelos/${id}`,
    ADMIN_UNIDADES: "/admin/unidades",
    ADMIN_UNIDAD: (id) => `/admin/unidades/${id}`,
    ADMIN_UNIDAD_COMANDOS: (id) => `/admin/unidades/${id}/comandos`,
    ADMIN_ASIGNAR: (id) => `/admin/unidades/${id}/asignar`,
    ADMIN_CLIENTES: "/admin/clientes",
    ADMIN_CLIENTE: (id) => `/admin/clientes/${id}`,
    ADMIN_AUDITORIA: (limit = 50) => `/admin/auditoria?limit=${limit}`,

    // 4.3 Usuario (Comprador)
    MIS_VEHICULOS: "/mis-vehiculos",
    AUTORIZAR_SOPORTE: (id) => `/mis-vehiculos/${id}/soporte`,

    // 4.3 Editor de Demos
    EDITOR_DEMOS_VEHICULO: (id) => `/editor-demos/vehiculo/${id}`,
    EDITOR_DEMOS: "/editor-demos",
    EDITOR_DEMO: (id) => `/editor-demos/${id}`,

    // 4.3 Invitado y Catálogo Público
    CATALOGO_PUBLICO: "/catalogo/publico",
    INVITADO_INICIAR: "/invitado/sesiones/iniciar",
    INVITADO_ACTUAL: "/invitado/sesiones/actual",
    INVITADO_FINALIZAR: "/invitado/sesiones/finalizar",
  },

  // Parámetros de monitoreo periódico
  HEALTH_CHECK_INTERVAL_MS: 8000,
  WS_RECONNECT_INTERVAL_MS: 3000,
  REQUEST_TIMEOUT_MS: 8000,
};
