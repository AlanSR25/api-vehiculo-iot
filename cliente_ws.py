import asyncio
import json
import ssl

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI, WebSocketException


URL = "wss://44.194.225.196/ws/vehiculo/1"


async def escuchar() -> None:
    print(f"Conectando a {URL}...")
    # Solo para esta práctica: el servidor utiliza un certificado autofirmado.
    contexto_ssl = ssl.create_default_context()
    contexto_ssl.check_hostname = False
    contexto_ssl.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(URL, ssl=contexto_ssl) as websocket:
            print("¡Conectado! Esperando eventos del vehículo...\n")
            while True:
                mensaje = await websocket.recv()
                datos = json.loads(mensaje)
                evento = datos.get("evento", "EVENTO_DESCONOCIDO")
                print(f"[{evento}] -> {json.dumps(datos, indent=2, ensure_ascii=False)}")
    except ConnectionRefusedError:
        print("No fue posible conectar. Inicia primero la API en el puerto 8000.")
    except ConnectionClosed as exc:
        print(f"El servidor cerró la conexión WebSocket: {exc}")
    except (InvalidURI, WebSocketException, json.JSONDecodeError) as exc:
        print(f"Error del cliente WebSocket: {exc}")


if __name__ == "__main__":
    try:
        asyncio.run(escuchar())
    except KeyboardInterrupt:
        print("\nCliente WebSocket detenido.")

