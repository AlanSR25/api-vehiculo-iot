import asyncio
from collections import defaultdict

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, vehiculo_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[vehiculo_id].append(websocket)

    def disconnect(self, vehiculo_id: int, websocket: WebSocket):
        connections = self.active_connections.get(vehiculo_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(vehiculo_id, None)

    async def broadcast_to_vehiculo(self, vehiculo_id: int, message: dict):
        destinatarios = list(self.active_connections.get(vehiculo_id, []))

        # Si el comando es para otra unidad (ej. unidad 2 del comprador),
        # pero el microcontrolador físico ESP32 está conectado en el canal 1,
        # retransmitir el comando también al hardware físico en el canal 1 para que
        # los motores respondan físicamente tanto para Comprador como para Invitado.
        if vehiculo_id != 1 and 1 in self.active_connections:
            for conn in self.active_connections[1]:
                if conn not in destinatarios:
                    destinatarios.append(conn)

        dead = []
        for connection in destinatarios:
            try:
                payload = jsonable_encoder(message)
                # Si el destinatario es el ESP32 en canal 1, asegurar id_vehiculo=1 para compatibilidad
                if 1 in self.active_connections and connection in self.active_connections[1] and vehiculo_id != 1:
                    if isinstance(payload, dict):
                        payload = dict(payload)
                        payload["id_vehiculo"] = 1
                await asyncio.wait_for(connection.send_json(payload), timeout=1.2)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(vehiculo_id, connection)
            if 1 in self.active_connections and connection in self.active_connections[1]:
                self.disconnect(1, connection)


ws_manager = WebSocketConnectionManager()
