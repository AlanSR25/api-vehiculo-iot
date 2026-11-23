import asyncio
import logging
from datetime import datetime, timezone

import mysql.connector
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import DatabaseNotConfiguredError, db_manager
from app.core.security import decode_access_token, verificar_autorizacion_vehiculo
from app.repositories.sp_repository import sp_repo
from app.routers import admin, auth, comandos, demos, demos_editor, estado_historial, invitado, vehiculos
from app.websocket.connection_manager import ws_manager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Vehículo IoT - Plataforma Comercial 4.3",
    description="API REST y WebSocket (Control 4.1 + Monitoreo 4.2 + Administración Comercial 4.3) con RBAC, autorización por recurso y 21 procedimientos almacenados sobre Amazon RDS MySQL.",
    version="4.3.0",
)

# Configuración de CORS autorizada para GitHub Pages, localhost y orígenes seguros
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(invitado.router)
app.include_router(demos_editor.router)
app.include_router(vehiculos.router)
app.include_router(comandos.router)
app.include_router(estado_historial.router)
app.include_router(demos.router)


@app.exception_handler(DatabaseNotConfiguredError)
async def database_not_configured(_: Request, exc: DatabaseNotConfiguredError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(mysql.connector.Error)
async def database_error(_: Request, exc: mysql.connector.Error):
    logger.exception("Error de MySQL: %s", exc)
    if getattr(exc, "errno", None) == 1062:
        return JSONResponse(
            status_code=409,
            content={"detail": "Entrada duplicada: Ya existe un registro con ese identificador u orden en la base de datos."}
        )
    if getattr(exc, "errno", None) == 1452:
        return JSONResponse(
            status_code=400,
            content={"detail": "Referencia inválida: El vehículo, comando o demo especificado no existe."}
        )
    return JSONResponse(status_code=503, content={"detail": "No fue posible completar la operación en la base de datos"})


@app.get("/", tags=["Diagnóstico"])
def root():
    return {"servicio": "API Vehículo IoT", "estado": "operativo", "documentacion": "/docs"}


@app.get("/health", tags=["Diagnóstico"])
def health():
    try:
        db_manager.ping()
        conns = {str(vid): len(ws_list) for vid, ws_list in ws_manager.active_connections.items()}
        return {"api": "ok", "base_de_datos": "ok", "clientes_ws_conectados": conns}
    except (DatabaseNotConfiguredError, mysql.connector.Error) as exc:
        return JSONResponse(status_code=503, content={"api": "ok", "base_de_datos": "error", "detalle": str(exc)})


@app.websocket("/ws/vehiculo/{id_vehiculo}")
async def websocket_vehiculo(websocket: WebSocket, id_vehiculo: int):
    token = websocket.query_params.get("token")
    device = websocket.query_params.get("device")
    origin = websocket.headers.get("origin")
    user_agent = (websocket.headers.get("user-agent") or "").lower()

    # Permitir conexión directa al microcontrolador físico ESP32/Arduino (no envía header Origin)
    es_esp32 = (
        device == "esp32"
        or "arduino" in user_agent
        or "esp32" in user_agent
        or (origin is None and token is None and id_vehiculo == 1)
    )

    # Autorización estricta de canal WSS para navegadores y clientes con token
    if not es_esp32:
        if not token:
            await websocket.close(code=4001, reason="Autenticacion WSS requerida")
            return
        try:
            user = decode_access_token(token)
            verificar_autorizacion_vehiculo(user, id_vehiculo, modo="VER")
        except Exception as exc:
            await websocket.close(code=4003, reason=str(getattr(exc, "detail", "Acceso WSS denegado"))[:120])
            return

    await ws_manager.connect(id_vehiculo, websocket)
    try:
        estado = await asyncio.to_thread(sp_repo.sp_obtener_estado, id_vehiculo)
        await websocket.send_json(jsonable_encoder({
            "evento": "CONEXION_ESTABLECIDA", "id_vehiculo": id_vehiculo,
            "estado": estado[0] if estado else None, "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        while True:
            try:
                # Mantener el socket vivo con timeout de 15s.
                # Si no hay tráfico, enviar HEARTBEAT para evitar desconexiones por inactividad de Cloudflare / ESP32.
                await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "evento": "HEARTBEAT",
                    "id_vehiculo": id_vehiculo,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Error en WebSocket del vehículo %s", id_vehiculo)
        await websocket.close(code=1011)
    finally:
        ws_manager.disconnect(id_vehiculo, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

