/**
 * wsService.js - Gestor de sesión WebSocket WSS nativo para el navegador
 */

import { CONFIG } from "../config.js";

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
    this.listeners = new Set();
    this.stateChangeListeners = new Set();
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

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this._setState(WsState.CONNECTING);

    try {
      this.ws = new WebSocket(CONFIG.WS_URL);

      this.ws.onopen = () => {
        this._setState(WsState.ONLINE);
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.listeners.forEach((cb) => cb(data));
        } catch {
          // Mensaje no JSON
        }
      };

      this.ws.onerror = () => {
        this._setState(WsState.DISCONNECTED);
      };

      this.ws.onclose = () => {
        this._setState(WsState.DISCONNECTED);
        this._scheduleReconnect();
      };
    } catch {
      this._setState(WsState.DISCONNECTED);
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, CONFIG.WS_RECONNECT_INTERVAL_MS);
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._setState(WsState.DISCONNECTED);
  }
}

export const wsService = new WebSocketService();

