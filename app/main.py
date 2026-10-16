import asyncio
import logging
from datetime import datetime, timezone

import mysql.connector
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.database import DatabaseNotConfiguredError, db_manager
from app.repositories.sp_repository import sp_repo
from app.routers import comandos, demos, estado_historial, vehiculos
from app.websocket.connection_manager import ws_manager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Vehículo IoT - Entorno Dev",
    description="API REST y WebSocket con 21 procedimientos almacenados sobre MySQL/Amazon RDS.",
    version="1.0.0",
)
app.include_router(vehiculos.router)
app.include_router(comandos.router)
app.include_router(estado_historial.router)
app.include_router(demos.router)


@app.exception_handler(DatabaseNotConfiguredError)
async def database_not_configured(_: Request, exc: DatabaseNotConfiguredError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(mysql.connector.Error)
async def database_error(_: Request, exc: mysql.connector.Error):
    logger.exception("Error de MySQL")
    return JSONResponse(status_code=503, content={"detail": "No fue posible completar la operación en la base de datos"})


@app.get("/", tags=["Diagnóstico"])
def root():
    return {"servicio": "API Vehículo IoT", "estado": "operativo", "documentacion": "/docs"}


@app.get("/health", tags=["Diagnóstico"])
def health():
    try:
        db_manager.ping()
        return {"api": "ok", "base_de_datos": "ok"}
    except (DatabaseNotConfiguredError, mysql.connector.Error) as exc:
        return JSONResponse(status_code=503, content={"api": "ok", "base_de_datos": "error", "detalle": str(exc)})


@app.websocket("/ws/vehiculo/{id_vehiculo}")
async def websocket_vehiculo(websocket: WebSocket, id_vehiculo: int):
    await ws_manager.connect(id_vehiculo, websocket)
    try:
        estado = await asyncio.to_thread(sp_repo.sp_obtener_estado, id_vehiculo)
        await websocket.send_json(jsonable_encoder({
            "evento": "CONEXION_ESTABLECIDA", "id_vehiculo": id_vehiculo,
            "estado": estado[0] if estado else None, "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        while True:
            await websocket.receive_text()
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

