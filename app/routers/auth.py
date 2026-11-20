"""
auth.py - Autenticación segura (Login, Logout con revocación real y perfil /auth/me).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import (
    create_access_token,
    get_current_user,
    revoke_token,
    verify_password,
)
from app.repositories.admin_repository import admin_repo
from app.websocket.connection_manager import ws_manager

router = APIRouter(prefix="/auth", tags=["Autenticación y Roles"])


class LoginRequest(BaseModel):
    correo: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=4, max_length=120)


@router.post("/login")
def login(datos: LoginRequest):
    user = admin_repo.get_user_by_email(datos.correo)
    if not user or not user.get("activo") or not verify_password(datos.password, user["password_hash"]):
        admin_repo.auditar(None, datos.correo, "ANONIMO", "LOGIN_FALLIDO", "auth/login", "RECHAZADO", "Credenciales inválidas")
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    token = create_access_token(
        {
            "id_usuario": user["id_usuario"],
            "correo": user["correo"],
            "nombre_completo": user["nombre_completo"],
            "rol": user["rol_codigo"],
        }
    )
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol_codigo"], "LOGIN", "auth/login", "EXITO", "Inicio de sesión exitoso")
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id_usuario": user["id_usuario"],
            "nombre_completo": user["nombre_completo"],
            "correo": user["correo"],
            "rol": user["rol_codigo"],
            "rol_nombre": user["rol_nombre"],
        },
    }


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    raw_token = user.get("_raw_token")
    if raw_token:
        revoke_token(raw_token)

    # Si tenía sesión de invitado activa, liberarla y detener vehículo por seguridad
    sesion_token = user.get("sesion_invitado_token")
    if sesion_token:
        sesion = admin_repo.get_sesion_por_token(sesion_token)
        if sesion and sesion.get("activa"):
            admin_repo.cerrar_sesion_invitado(sesion_token, "LOGOUT")
            await ws_manager.broadcast_to_vehiculo(
                sesion["id_vehiculo"],
                {
                    "evento": "MOVIMIENTO_INDIVIDUAL",
                    "id_vehiculo": sesion["id_vehiculo"],
                    "codigo": 9,
                    "comando": "DETENER",
                    "origen": "CIERRE_SESION_INVITADO",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    admin_repo.auditar(user.get("id_usuario"), user.get("correo"), user.get("rol"), "LOGOUT", "auth/logout", "EXITO", "Sesión cerrada y token revocado")
    return {"mensaje": "Sesión cerrada correctamente"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    sesion_info = None
    if user.get("sesion_invitado_token"):
        s = admin_repo.get_sesion_por_token(user["sesion_invitado_token"])
        if s and s.get("activa"):
            sesion_info = {
                "id_sesion": s["id_sesion"],
                "id_vehiculo": s["id_vehiculo"],
                "segundos_restantes": max(0, int(s.get("segundos_restantes") or 0)),
                "comandos_permitidos": s["comandos_permitidos"],
            }
    return {
        "id_usuario": user.get("id_usuario"),
        "nombre_completo": user.get("nombre_completo"),
        "correo": user.get("correo"),
        "rol": user.get("rol"),
        "sesion_invitado": sesion_info,
    }
