from fastapi import APIRouter, HTTPException

from app.models.schemas import DemoActualizar, DemoCrear, DemoMovimientoActualizar, DemoMovimientoCrear
from app.repositories.sp_repository import sp_repo
from app.services.demo_runner import demo_runner

router = APIRouter(tags=["Demos y secuencias"])


@router.get("/vehiculos/{id_vehiculo}/demos")
def listar_demos(id_vehiculo: int): return sp_repo.sp_obtener_demos(id_vehiculo)


@router.post("/demos", status_code=201)
def crear_demo(datos: DemoCrear): return sp_repo.sp_crear_demo(datos.id_vehiculo, datos.nombre, datos.descripcion)


@router.put("/demos/{id_demo}")
def actualizar_demo(id_demo: int, datos: DemoActualizar):
    sp_repo.sp_actualizar_demo(id_demo, datos.nombre, datos.descripcion, datos.activo)
    return {"mensaje": "Demo actualizada"}


@router.delete("/demos/{id_demo}")
def eliminar_demo(id_demo: int):
    sp_repo.sp_eliminar_demo(id_demo)
    return {"mensaje": "Demo eliminada"}


@router.get("/demos/{id_demo}/movimientos")
def obtener_movimientos(id_demo: int): return sp_repo.sp_obtener_movimientos_demo(id_demo)


@router.post("/demos/{id_demo}/movimientos", status_code=201)
def agregar_movimiento(id_demo: int, datos: DemoMovimientoCrear):
    return sp_repo.sp_agregar_movimiento_demo(id_demo, datos.id_comando, datos.orden, datos.duracion_ms, datos.pausa_ms)


@router.put("/demos/movimientos/{id_movimiento}")
def actualizar_movimiento(id_movimiento: int, datos: DemoMovimientoActualizar):
    sp_repo.sp_actualizar_movimiento_demo(id_movimiento, datos.id_comando, datos.orden, datos.duracion_ms, datos.pausa_ms)
    return {"mensaje": "Movimiento actualizado"}


@router.delete("/demos/movimientos/{id_movimiento}")
def eliminar_movimiento(id_movimiento: int):
    sp_repo.sp_eliminar_movimiento_demo(id_movimiento)
    return {"mensaje": "Movimiento eliminado"}


@router.post("/vehiculos/{id_vehiculo}/demos/{id_demo}/iniciar", status_code=202)
async def iniciar_demo(id_vehiculo: int, id_demo: int):
    if demo_runner.is_running(id_vehiculo):
        raise HTTPException(409, "Ya existe una demo en ejecución para este vehículo")
    movimientos = sp_repo.sp_obtener_movimientos_demo(id_demo)
    if not movimientos:
        raise HTTPException(404, "La demo no contiene movimientos")
    demo_runner.start(id_vehiculo, id_demo)
    return {"resultado": "DEMO_INICIADA", "id_vehiculo": id_vehiculo, "id_demo": id_demo, "total_movimientos": len(movimientos)}


@router.post("/vehiculos/{id_vehiculo}/demos/cancelar")
def cancelar_demo(id_vehiculo: int):
    if not demo_runner.cancel_demo(id_vehiculo):
        raise HTTPException(400, "No hay ninguna demo activa para este vehículo")
    return {"mensaje": "Señal de cancelación enviada"}
