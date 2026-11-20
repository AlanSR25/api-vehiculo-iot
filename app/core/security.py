"""
security.py - Autenticación JWT HS256, Hashing PBKDF2-SHA256, RBAC y Autorización por Recurso (ABAC).
Sin dependencias externas frágiles (100% Python stdlib + FastAPI).
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request

from app.core.config import settings
from app.repositories.admin_repository import admin_repo

# Lista de tokens revocados en memoria (logout inmediato)
revoked_tokens: set[str] = set()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256$100000${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False


def create_access_token(payload: dict, expires_minutes: Optional[int] = None) -> str:
    exp_min = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRES_MINUTES
    now = int(time.time())
    body = {
        **payload,
        "iat": now,
        "exp": now + int(exp_min * 60),
        "jti": secrets.token_hex(8),
    }
    header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> dict:
    if not token or token in revoked_tokens:
        raise HTTPException(status_code=401, detail="Sesión inválida o cerrada")
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Formato JWT inválido")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(sig_b64), expected_sig):
            raise ValueError("Firma inválida")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise HTTPException(status_code=401, detail="Sesión expirada. Inicia sesión nuevamente.")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token de autenticación inválido")


def revoke_token(token: str) -> None:
    if token:
        revoked_tokens.add(token)


def extract_bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query_params.get("token")


def get_current_user(request: Request) -> dict:
    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Autenticación requerida (Bearer token)")
    payload = decode_access_token(token)
    payload["_raw_token"] = token

    # Si es usuario registrado (no invitado anónimo express), verificar que siga activo en RDS
    uid = payload.get("id_usuario")
    if uid:
        db_user = admin_repo.get_user_by_id(uid)
        if not db_user or not db_user.get("activo"):
            raise HTTPException(status_code=401, detail="Usuario inactivo o inexistente")
        payload["rol"] = db_user["rol_codigo"]
        payload["correo"] = db_user["correo"]
        payload["nombre_completo"] = db_user["nombre_completo"]
    return payload


def require_roles(*allowed_roles: str):
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("rol") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Acceso prohibido: se requiere rol {' o '.join(allowed_roles)} (rol actual: {user.get('rol')})",
            )
        return user
    return _checker


def verificar_autorizacion_vehiculo(
    user: dict,
    id_vehiculo: int,
    modo: str = "VER",
    comando_codigo: Optional[int] = None,
) -> dict:
    """
    Autorización por recurso (anti-IDOR / anti-BOLA):
    - modo='VER': consulta de estado, historial, comandos, demos o suscripción WSS.
    - modo='OPERAR': envío de comandos físicos o ejecución de demos.
    """
    admin_repo.expirar_sesiones_vencidas()
    unidad = admin_repo.get_unidad(id_vehiculo)
    if not unidad or not unidad.get("activo"):
        raise HTTPException(status_code=404, detail="Unidad de vehículo no encontrada o inactiva")

    rol = user.get("rol")
    uid = user.get("id_usuario")
    estado_com = unidad.get("estado_comercial", "EXHIBICION")
    propietario = unidad.get("id_propietario")

    # 1. ROL USUARIO (Comprador)
    if rol == "USUARIO":
        if propietario != uid:
            admin_repo.auditar(uid, user.get("correo"), rol, f"ACCESO_DENEGADO_{modo}", f"vehiculo:{id_vehiculo}", "BLOQUEADO", "Intento de acceso a unidad ajena (IDOR)")
            raise HTTPException(status_code=403, detail="Acceso prohibido: esta unidad no pertenece a tu cuenta")
        return unidad

    # 2. ROL ADMIN (Empresa)
    if rol == "ADMIN":
        if modo == "OPERAR":
            if estado_com == "VENDIDO" and propietario and propietario != uid and not unidad.get("soporte_autorizado"):
                admin_repo.auditar(uid, user.get("correo"), rol, "SOPORTE_NO_AUTORIZADO", f"vehiculo:{id_vehiculo}", "BLOQUEADO", "Admin intentó operar unidad vendida sin consentimiento")
                raise HTTPException(
                    status_code=403,
                    detail="Unidad vendida: el Administrador requiere autorización explícita de soporte del propietario para operarla",
                )
            # Verificar que no haya una sesión de invitado exclusiva activa de otro usuario
            sesion_activa = admin_repo.get_sesion_activa_vehiculo(id_vehiculo)
            if sesion_activa and comando_codigo != 9:
                raise HTTPException(
                    status_code=409,
                    detail=f"Unidad reservada temporalmente por invitado ({sesion_activa['nombre_invitado']}). Solo se permite DETENER (9).",
                )
        return unidad

    # 3. ROL INVITADO (Prospecto / Exhibición)
    if rol == "INVITADO":
        if estado_com != "EXHIBICION":
            admin_repo.auditar(uid, user.get("correo"), rol, "INVITADO_UNIDAD_PRIVADA", f"vehiculo:{id_vehiculo}", "BLOQUEADO", "Invitado intentó acceder a unidad no pública")
            raise HTTPException(status_code=403, detail="Acceso prohibido: el Invitado solo puede interactuar con unidades de exhibición")

        sesion_token = user.get("sesion_invitado_token")
        sesion = admin_repo.get_sesion_por_token(sesion_token) if sesion_token else None
        if not sesion or not sesion.get("activa") or sesion.get("id_vehiculo") != id_vehiculo:
            raise HTTPException(status_code=403, detail="Se requiere una reserva temporal activa para esta unidad de exhibición")

        if modo == "OPERAR" and comando_codigo is not None:
            permitidos = {int(x.strip()) for x in str(sesion.get("comandos_permitidos", "1,2,3,4,7,9")).split(",") if x.strip().isdigit()}
            if int(comando_codigo) not in permitidos:
                raise HTTPException(
                    status_code=403,
                    detail=f"Comando #{comando_codigo} restringido en modo Invitado. Permitidos: {sorted(permitidos)}",
                )
        return unidad

    raise HTTPException(status_code=403, detail="Rol no autorizado")
