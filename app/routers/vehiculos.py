from fastapi import APIRouter, HTTPException

from app.models.schemas import VehiculoActualizar, VehiculoCrear
from app.repositories.sp_repository import sp_repo

router = APIRouter(prefix="/vehiculos", tags=["Vehículos"])


@router.get("")
def listar_vehiculos(): return sp_repo.sp_obtener_vehiculos()


@router.get("/{id_vehiculo}")
def obtener_vehiculo(id_vehiculo: int):
    result = sp_repo.sp_obtener_vehiculo(id_vehiculo)
    if not result:
        raise HTTPException(404, "Vehículo no encontrado")
    return result[0]


@router.post("", status_code=201)
def crear_vehiculo(datos: VehiculoCrear):
    return sp_repo.sp_crear_vehiculo(datos.nombre, datos.modelo, datos.descripcion, datos.microcontrolador)


@router.put("/{id_vehiculo}")
def actualizar_vehiculo(id_vehiculo: int, datos: VehiculoActualizar):
    sp_repo.sp_actualizar_vehiculo(id_vehiculo, datos.nombre, datos.modelo, datos.descripcion, datos.microcontrolador, datos.activo)
    return {"mensaje": "Vehículo actualizado"}


@router.delete("/{id_vehiculo}")
def eliminar_vehiculo(id_vehiculo: int):
    sp_repo.sp_eliminar_vehiculo(id_vehiculo)
    return {"mensaje": "Vehículo eliminado"}

