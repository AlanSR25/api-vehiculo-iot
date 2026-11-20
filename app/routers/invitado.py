"""
invitado.py - Catálogo público y sesiones temporales exclusivas de exhibición para Invitados.
"""
import asyncio
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.repositories.admin_repository import admin_repo
from app.websocket.connection_manager import ws_manager

router = APIRouter(tags=["Invitados y Exhibición Pública (4.3)"])


class IniciarSesionInvitadoRequest(BaseModel):
    id_vehiculo: int = Field(gt=0)
    nombre_invitado: str = Field(default="Prospecto Web", min_length=2, max_length=80)
    duracion_segundos: int = Field(default=90, ge=30, le=180)


async def _auto_detener_al_expirar(token_sesion: str, id_vehiculo: int, duracion_seg: int):
    await asyncio.sleep(duracion_seg + 1)
    sesion = admin_repo.get_sesion_por_token(token_sesion)
    if sesion and sesion.get("activa"):
        admin_repo.cerrar_sesion_invitado(token_sesion, "EXPIRADA_AUTO")
        await ws_manager.broadcast_to_vehiculo(
            id_vehiculo,
            {
                "evento": "MOVIMIENTO_INDIVIDUAL",
                "id_vehiculo": id_vehiculo,
                "codigo": 9,
                "comando": "DETENER",
                "origen": "EXPIRACION_INVITADO",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await ws_manager.broadcast_to_vehiculo(
            id_vehiculo,
            {
                "evento": "SESION_INVITADO_EXPIRADA",
                "id_vehiculo": id_vehiculo,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


@router.get("/catalogo/publico")
def catalogo_publico():
    """Catálogo público para prospectos: NO expone inventario privado ni datos de compradores."""
    modelos = admin_repo.list_modelos(solo_activos=True)
    exhibicion = admin_repo.list_unidades_exhibicion_publicas()
    return {
        "modelos": modelos,
        "unidades_exhibicion": [
            {
                "id_vehiculo": u["id_vehiculo"],
                "numero_serie": u["numero_serie"],
                "nombre": u["nombre"],
                "modelo_comercial": u["modelo_comercial"] or u["modelo"],
                "categoria": u["categoria"] or "Vehículo IoT",
                "descripcion": u["descripcion"],
                "microcontrolador": u["microcontrolador"],
                "imagen_icono": u["imagen_icono"] or "bi-truck-front",
                "disponible": u["sesion_activa_id"] is None,
                "ocupado_por": u["ocupado_por"] if u["sesion_activa_id"] else None,
                "segundos_restantes": int(u["segundos_restantes"] or 0),
                "comandos_invitado": [1, 2, 3, 4, 7, 9],
            }
            for u in exhibicion
        ],
    }


@router.post("/invitado/sesiones/iniciar", status_code=201)
async def iniciar_sesion_invitado(datos: IniciarSesionInvitadoRequest):
    admin_repo.expirar_sesiones_vencidas()
    unidad = admin_repo.get_unidad(datos.id_vehiculo)
    if not unidad or not unidad.get("activo") or unidad.get("estado_comercial") != "EXHIBICION":
        raise HTTPException(403, "Esta unidad no está disponible para demostración pública de invitados")

    # Exclusividad: bloquear segunda sesión simultánea
    activa = admin_repo.get_sesion_activa_vehiculo(datos.id_vehiculo)
    if activa:
        restantes = max(1, int(activa.get("segundos_restantes") or 1))
        raise HTTPException(
            409,
            f"Unidad ocupada por {activa['nombre_invitado']}. Intenta de nuevo en {restantes} segundos.",
        )

    duracion = min(datos.duracion_segundos, settings.INVITADO_MAX_SECONDS)
    token_sesion = secrets.token_hex(24)
    comandos_permitidos = "1,2,3,4,7,9"

    sesion_id = admin_repo.crear_sesion_invitado(
        id_vehiculo=datos.id_vehiculo,
        nombre_invitado=datos.nombre_invitado,
        token_sesion=token_sesion,
        duracion_seg=duracion,
        comandos_permitidos=comandos_permitidos,
    )

    jwt_token = create_access_token(
        {
            "id_usuario": None,
            "correo": f"invitado_{sesion_id}@exhibicion.iot",
            "nombre_completo": datos.nombre_invitado,
            "rol": "INVITADO",
            "sesion_invitado_token": token_sesion,
            "id_vehiculo_reservado": datos.id_vehiculo,
        },
        expires_minutes=max(1, (duracion // 60) + 1),
    )

    admin_repo.auditar(
        None,
        f"invitado:{datos.nombre_invitado}",
        "INVITADO",
        "INICIAR_SESION_EXHIBICION",
        f"vehiculo:{datos.id_vehiculo}",
        "EXITO",
        f"Reserva exclusiva por {duracion}s",
    )

    asyncio.create_task(_auto_detener_al_expirar(token_sesion, datos.id_vehiculo, duracion))

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "sesion": {
            "id_sesion": sesion_id,
            "id_vehiculo": datos.id_vehiculo,
            "nombre_vehiculo": unidad["nombre"],
            "nombre_invitado": datos.nombre_invitado,
            "duracion_segundos": duracion,
            "comandos_permitidos": [1, 2, 3, 4, 7, 9],
        },
    }


@router.get("/invitado/sesiones/actual")
def sesion_actual(user: dict = Depends(get_current_user)):
    token_sesion = user.get("sesion_invitado_token")
    if not token_sesion:
        raise HTTPException(404, "No tienes una sesión temporal de invitado activa")
    sesion = admin_repo.get_sesion_por_token(token_sesion)
    if not sesion or not sesion.get("activa"):
        raise HTTPException(410, "Tu sesión temporal ha finalizado o expirado")
    return {
        "id_sesion": sesion["id_sesion"],
        "id_vehiculo": sesion["id_vehiculo"],
        "segundos_restantes": max(0, int(sesion.get("segundos_restantes") or 0)),
        "comandos_permitidos": [int(x) for x in sesion["comandos_permitidos"].split(",") if x.isdigit()],
    }


@router.post("/invitado/sesiones/finalizar")
async def finalizar_sesion_invitado(user: dict = Depends(get_current_user)):
    token_sesion = user.get("sesion_invitado_token")
    if not token_sesion:
        raise HTTPException(400, "No hay una sesión de invitado activa para cerrar")
    sesion = admin_repo.get_sesion_por_token(token_sesion)
    if sesion and sesion.get("activa"):
        admin_repo.cerrar_sesion_invitado(token_sesion, "FINALIZADA_MANUAL")
        await ws_manager.broadcast_to_vehiculo(
            sesion["id_vehiculo"],
            {
                "evento": "MOVIMIENTO_INDIVIDUAL",
                "id_vehiculo": sesion["id_vehiculo"],
                "codigo": 9,
                "comando": "DETENER",
                "origen": "FIN_SESION_INVITADO",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        admin_repo.auditar(None, user.get("correo"), "INVITADO", "FINALIZAR_SESION_EXHIBICION", f"vehiculo:{sesion['id_vehiculo']}", "EXITO", "Reserva liberada y DETENER emitido")
    return {"mensaje": "Sesión finalizada, reserva liberada y comando DETENER enviado"}
