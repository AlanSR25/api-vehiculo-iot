"""
demos_editor.py - Editor visual persistente de Demos de Fábrica (Admin) y Demos Privadas (Usuario).
Valida capacidades del vehículo, límites de duración y propiedad del recurso.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_roles, verificar_autorizacion_vehiculo
from app.repositories.admin_repository import admin_repo
from app.repositories.sp_repository import sp_repo

router = APIRouter(prefix="/editor-demos", tags=["Editor de Demos (4.3)"])


class PasoDemoInput(BaseModel):
    id_comando: int = Field(gt=0)
    duracion_ms: int = Field(ge=200, le=5000)
    pausa_ms: int = Field(default=250, ge=0, le=3000)


class DemoCompletaInput(BaseModel):
    id_vehiculo: int = Field(gt=0)
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: Optional[str] = Field(default="", max_length=255)
    pasos: list[PasoDemoInput] = Field(min_length=1, max_length=15)


def _validar_pasos_vehiculo(id_vehiculo: int, pasos: list[PasoDemoInput]):
    comandos = sp_repo.sp_obtener_comandos_vehiculo(id_vehiculo)
    valid_ids = {c["id_comando"] for c in comandos if c.get("activo")}
    for idx, paso in enumerate(pasos, start=1):
        if paso.id_comando not in valid_ids:
            raise HTTPException(
                400,
                f"Paso #{idx}: el comando id={paso.id_comando} no es compatible con las capacidades del vehículo #{id_vehiculo}",
            )


@router.get("/vehiculo/{id_vehiculo}")
def listar_demos_editor(id_vehiculo: int, user: dict = Depends(get_current_user)):
    verificar_autorizacion_vehiculo(user, id_vehiculo, modo="VER")
    return admin_repo.list_demos_con_pasos(id_vehiculo, user)


@router.post("", status_code=201)
def crear_demo_completa(datos: DemoCompletaInput, user: dict = Depends(require_roles("ADMIN", "USUARIO"))):
    verificar_autorizacion_vehiculo(user, datos.id_vehiculo, modo="VER")
    _validar_pasos_vehiculo(datos.id_vehiculo, datos.pasos)

    tipo_demo = "FABRICA" if user["rol"] == "ADMIN" else "PRIVADA"
    demo_id = admin_repo.save_demo_completa(
        id_vehiculo=datos.id_vehiculo,
        nombre=datos.nombre,
        descripcion=datos.descripcion or "",
        id_usuario=user["id_usuario"],
        tipo_demo=tipo_demo,
        pasos=[p.model_dump() for p in datos.pasos],
    )
    admin_repo.auditar(
        user["id_usuario"],
        user["correo"],
        user["rol"],
        "CREAR_DEMO",
        f"demo:{demo_id}",
        "EXITO",
        f"Vehículo #{datos.id_vehiculo}, {len(datos.pasos)} pasos ({tipo_demo})",
    )
    return {"id_demo": demo_id, "tipo_demo": tipo_demo, "mensaje": "Demo guardada en Amazon RDS"}


@router.put("/{id_demo}")
def editar_demo_completa(id_demo: int, datos: DemoCompletaInput, user: dict = Depends(require_roles("ADMIN", "USUARIO"))):
    demo = admin_repo.get_demo(id_demo)
    if not demo or not demo.get("activo"):
        raise HTTPException(404, "Demo no encontrada")
    if user["rol"] == "USUARIO" and (demo.get("tipo_demo") == "FABRICA" or demo.get("id_usuario") != user["id_usuario"]):
        raise HTTPException(403, "No tienes permiso para editar una demo de fábrica o de otro usuario")

    verificar_autorizacion_vehiculo(user, demo["id_vehiculo"], modo="VER")
    _validar_pasos_vehiculo(demo["id_vehiculo"], datos.pasos)

    admin_repo.save_demo_completa(
        id_vehiculo=demo["id_vehiculo"],
        nombre=datos.nombre,
        descripcion=datos.descripcion or "",
        id_usuario=demo.get("id_usuario"),
        tipo_demo=demo.get("tipo_demo", "PRIVADA"),
        pasos=[p.model_dump() for p in datos.pasos],
        id_demo_editar=id_demo,
    )
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "EDITAR_DEMO", f"demo:{id_demo}", "EXITO", f"{len(datos.pasos)} pasos")
    return {"id_demo": id_demo, "mensaje": "Demo actualizada correctamente"}


@router.delete("/{id_demo}")
def eliminar_demo_editor(id_demo: int, user: dict = Depends(require_roles("ADMIN", "USUARIO"))):
    demo = admin_repo.get_demo(id_demo)
    if not demo or not demo.get("activo"):
        raise HTTPException(404, "Demo no encontrada")
    if user["rol"] == "USUARIO" and (demo.get("tipo_demo") == "FABRICA" or demo.get("id_usuario") != user["id_usuario"]):
        raise HTTPException(403, "No tienes permiso para eliminar una demo ajena o de fábrica")

    admin_repo.delete_demo_logica(id_demo)
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "ELIMINAR_DEMO", f"demo:{id_demo}", "EXITO", demo["nombre"])
    return {"mensaje": "Demo eliminada correctamente"}
