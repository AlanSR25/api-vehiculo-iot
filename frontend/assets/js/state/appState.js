/**
 * appState.js - Estado operacional centralizado reactivo
 */

export const appState = {
  // Vehículo
  vehiculo: null,
  comandos: [],
  demos: [],

  // Operación
  comandoActivo: null,
  demoActiva: false,
  demoEnCurso: null,
  solicitudPendiente: false,

  // Indicadores
  wsEstado: "DISCONNECTED",
  apiEstado: "COMPROBANDO",
  rdsEstado: "SIN_VERIFICAR",

  // Última acción
  ultimaAccion: {
    solicitada: "Ninguna",
    aceptadaHttp: false,
    eventoWs: null,
    timestamp: null,
  },

  // Observadores
  _subscribers: new Set(),

  subscribe(callback) {
    this._subscribers.add(callback);
    return () => this._subscribers.delete(callback);
  },

  notify() {
    this._subscribers.forEach((cb) => cb(this));
  },
};

