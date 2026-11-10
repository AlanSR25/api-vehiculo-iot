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
        dead = []
        for connection in list(self.active_connections.get(vehiculo_id, [])):
            try:
                await connection.send_json(jsonable_encoder(message))
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(vehiculo_id, connection)


ws_manager = WebSocketConnectionManager()
