import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.schemas import EstadoActualizar, MovimientoIndividual
from app.repositories.sp_repository import sp_repo
from app.websocket.connection_manager import ws_manager

router = APIRouter(tags=["Estado e historial"])


@router.get("/vehiculos/{id_vehiculo}/estado")
def obtener_estado(id_vehiculo: int):
    result = sp_repo.sp_obtener_estado(id_vehiculo)
    return result[0] if result else {}


@router.put("/vehiculos/{id_vehiculo}/estado")
def actualizar_estado(id_vehiculo: int, datos: EstadoActualizar):
    sp_repo.sp_actualizar_estado(id_vehiculo, datos.id_comando, datos.conectado)
    return {"mensaje": "Estado actualizado"}


@router.get("/vehiculos/{id_vehiculo}/historial")
def obtener_historial(id_vehiculo: int): return sp_repo.sp_obtener_historial(id_vehiculo)[:10]


@router.post("/vehiculos/{id_vehiculo}/movimiento")
async def ejecutar_movimiento(id_vehiculo: int, datos: MovimientoIndividual):
    vehiculos, comandos = await asyncio.gather(
        asyncio.to_thread(sp_repo.sp_obtener_vehiculo, id_vehiculo),
        asyncio.to_thread(sp_repo.sp_obtener_comandos_vehiculo, id_vehiculo),
    )
    if not vehiculos or not vehiculos[0].get("activo"):
        raise HTTPException(404, "Vehículo no encontrado o inactivo")
    comando = next((c for c in comandos if c["id_comando"] == datos.id_comando and c.get("activo")), None)
    if not comando:
        raise HTTPException(400, "Comando inválido o no pertenece a este vehículo")
    await asyncio.to_thread(sp_repo.ejecutar_movimiento_individual_tx, id_vehiculo, datos.id_comando, True, datos.origen)
    await ws_manager.broadcast_to_vehiculo(id_vehiculo, {
        "evento": "MOVIMIENTO_INDIVIDUAL", "id_vehiculo": id_vehiculo,
        "comando": comando["nombre"], "codigo": comando["codigo"], "origen": datos.origen,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"resultado": "EXITO", "id_vehiculo": id_vehiculo, "codigo": comando["codigo"]}

