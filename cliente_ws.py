import asyncio
import json
import ssl
import sys

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI, WebSocketException


URL_DEFAULT = "wss://44.194.225.196:8000/ws/vehiculo/1"


async def escuchar(url: str = URL_DEFAULT) -> None:
    print(f"Conectando a {url}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(url, ssl=ctx) as websocket:
            print("¡Conectado exitosamente! Esperando eventos del vehículo en tiempo real...\n")
            while True:
                mensaje = await websocket.recv()
                datos = json.loads(mensaje)
                evento = datos.get("evento", "EVENTO_DESCONOCIDO")
                print(f"[{evento}] -> {json.dumps(datos, indent=2, ensure_ascii=False)}\n")
    except ConnectionRefusedError:
        print("No fue posible conectar. Verifica que el servidor esté activo.")
    except ConnectionClosed as exc:
        print(f"El servidor cerró la conexión WebSocket: {exc}")
    except (InvalidURI, WebSocketException, json.JSONDecodeError) as exc:
        print(f"Error del cliente WebSocket: {exc}")


if __name__ == "__main__":
    url_objetivo = sys.argv[1] if len(sys.argv) > 1 else URL_DEFAULT
    try:
        asyncio.run(escuchar(url_objetivo))
    except KeyboardInterrupt:
        print("\nCliente WebSocket detenido.")
