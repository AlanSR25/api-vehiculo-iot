/**
 * wsService.js - Gestor de sesión WebSocket WSS autenticado y dinámico por vehículo.
 * Evita conexiones duplicadas y cancela suscripciones al cambiar de unidad o cerrar sesión.
 */

import { CONFIG } from "../config.js?v=20261123c";

export const WsState = {
  CONNECTING: "CONNECTING",
  ONLINE: "ONLINE",
  DISCONNECTED: "DISCONNECTED",
};

class WebSocketService {
  constructor() {
    this.ws = null;
    this.state = WsState.DISCONNECTED;
    this.reconnectTimer = null;
    this.pingTimer = null;
    this.listeners = new Set();
    this.stateChangeListeners = new Set();
    this.currentVehicleId = null;
    this.currentToken = null;
    this.manualDisconnect = false;
  }

  onMessage(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  onStateChange(callback) {
    this.stateChangeListeners.add(callback);
    callback(this.state);
    return () => this.stateChangeListeners.delete(callback);
  }

  _setState(newState) {
    if (this.state !== newState) {
      this.state = newState;
      this.stateChangeListeners.forEach((cb) => cb(newState));
    }
  }

  _startPing() {
    this._stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ tipo: "PING", ts: Date.now() }));
        } catch {
          // ignore
        }
      }
    }, 12000);
  }

  _stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        const text = typeof data === "string" ? data : JSON.stringify(data);
        this.ws.send(text);
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }

  connect(vehicleId = this.currentVehicleId, token = this.currentToken) {
    if (!vehicleId || !token) {
      this.disconnect();
      return;
    }

    // Si cambia de vehículo o token, cerrar la conexión previa limpiamente
    if (
      this.ws &&
      (this.currentVehicleId !== vehicleId || this.currentToken !== token)
    ) {
      this.disconnect();
    }

    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.currentVehicleId = vehicleId;
    this.currentToken = token;
    this.manualDisconnect = false;
    this._setState(WsState.CONNECTING);

    const url = `${CONFIG.WS_BASE_URL}/${vehicleId}?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this._setState(WsState.ONLINE);
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
        this._startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Si es un Heartbeat de mantenimiento, solo confirmar actividad
          if (data && data.evento === "HEARTBEAT") {
            return;
          }
          this.listeners.forEach((cb) => cb(data));
        } catch {
          // Mensaje no JSON
        }
      };

      this.ws.onerror = () => {
        this._setState(WsState.DISCONNECTED);
      };

      this.ws.onclose = (ev) => {
        this._stopPing();
        this._setState(WsState.DISCONNECTED);
        // No reconectar si fue cierre manual o rechazo de autorización (4001/4003)
        if (!this.manualDisconnect && ev.code !== 4001 && ev.code !== 4003) {
          this._scheduleReconnect();
        }
      };
    } catch {
      this._stopPing();
      this._setState(WsState.DISCONNECTED);
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (!this.reconnectTimer && !this.manualDisconnect && this.currentVehicleId && this.currentToken) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect(this.currentVehicleId, this.currentToken);
      }, 1200);
    }
  }

  disconnect() {
    this.manualDisconnect = true;
    this._stopPing();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try {
        this.ws.onclose = null;
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }
    this._setState(WsState.DISCONNECTED);
  }
}

export const wsService = new WebSocketService();
