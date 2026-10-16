from fastapi import APIRouter

from app.models.schemas import ComandoActualizar, ComandoCrear
from app.repositories.sp_repository import sp_repo

router = APIRouter(prefix="/comandos", tags=["Comandos"])


@router.get("/vehiculo/{id_vehiculo}")
def listar_comandos(id_vehiculo: int): return sp_repo.sp_obtener_comandos_vehiculo(id_vehiculo)


@router.post("", status_code=201)
def crear_comando(datos: ComandoCrear):
    return sp_repo.sp_crear_comando(datos.id_vehiculo, datos.nombre, datos.codigo, datos.descripcion)


@router.put("/{id_comando}")
def actualizar_comando(id_comando: int, datos: ComandoActualizar):
    sp_repo.sp_actualizar_comando(id_comando, datos.nombre, datos.codigo, datos.descripcion, datos.activo)
    return {"mensaje": "Comando actualizado"}


@router.delete("/{id_comando}")
def eliminar_comando(id_comando: int):
    sp_repo.sp_eliminar_comando(id_comando)
    return {"mensaje": "Comando eliminado"}

