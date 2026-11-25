"""
admin.py - Módulo comercial 4.3:
Dashboard, Modelos Comerciales, Unidades Físicas, Clientes, Asignaciones, Auditoría y Mis Vehículos.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user, hash_password, require_roles
from app.repositories.admin_repository import admin_repo
from app.routers.estado_historial import invalidar_cache_vehiculo
from app.websocket.connection_manager import ws_manager

router = APIRouter(tags=["Administración Comercial (4.3)"])


class ModeloCrear(BaseModel):
    codigo_modelo: str = Field(min_length=2, max_length=40)
    nombre: str = Field(min_length=2, max_length=100)
    categoria: str = Field(default="Vehículo IoT", max_length=60)
    descripcion: Optional[str] = Field(default="", max_length=255)
    comandos_soportados: str = Field(default="1,2,3,4,5,6,7,8,9", max_length=60)
    precio_referencia: float = Field(default=0.0, ge=0)
    imagen_icono: str = Field(default="bi-truck-front", max_length=60)


class ModeloActualizar(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    categoria: str = Field(default="Vehículo IoT", max_length=60)
    descripcion: Optional[str] = Field(default="", max_length=255)
    comandos_soportados: str = Field(default="1,2,3,4,5,6,7,8,9", max_length=60)
    precio_referencia: float = Field(default=0.0, ge=0)
    activo: bool = True


class UnidadCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    numero_serie: str = Field(min_length=3, max_length=60)
    id_modelo: int = Field(gt=0)
    microcontrolador: str = Field(default="ESP32", max_length=50)
    descripcion: Optional[str] = Field(default="", max_length=255)
    estado_comercial: str = Field(default="DISPONIBLE")
    id_propietario: Optional[int] = None


class UnidadActualizar(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: Optional[str] = Field(default="", max_length=255)
    estado_comercial: str
    activo: bool = True


class AsignarUnidadRequest(BaseModel):
    id_propietario: Optional[int] = None
    estado_comercial: str = Field(default="VENDIDO")


class ClienteCrear(BaseModel):
    nombre_completo: str = Field(min_length=2, max_length=120)
    correo: str = Field(min_length=4, max_length=120)
    password: str = Field(min_length=6, max_length=120)
    telefono: Optional[str] = Field(default=None, max_length=30)
    rol_codigo: str = Field(default="USUARIO")


class ClienteActualizar(BaseModel):
    nombre_completo: str = Field(min_length=2, max_length=120)
    telefono: Optional[str] = Field(default=None, max_length=30)
    activo: bool = True
    rol_codigo: Optional[str] = None


class SoporteAutorizarRequest(BaseModel):
    autorizado: bool


class ComandosUnidadActualizar(BaseModel):
    codigos_habilitados: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 7, 9])


ESTADOS_VALIDOS = {"DISPONIBLE", "VENDIDO", "EXHIBICION", "MANTENIMIENTO", "INACTIVO"}


# =========================================================================
# DASHBOARD (SOLO ADMIN)
# =========================================================================
@router.get("/admin/dashboard")
def dashboard(user: dict = Depends(require_roles("ADMIN"))):
    metrics = admin_repo.get_dashboard_metrics()
    conns = {str(vid): len(ws_list) for vid, ws_list in ws_manager.active_connections.items()}
    return {
        "metricas": metrics,
        "sesiones_wss_navegador": conns,
        "nota_conectividad": "Las sesiones WSS reflejan navegadores/clientes conectados al servidor, no garantizan presencia física del microcontrolador.",
    }


# =========================================================================
# CRUD MODELOS COMERCIALES (SOLO ADMIN)
# =========================================================================
@router.get("/admin/modelos")
def listar_modelos(user: dict = Depends(require_roles("ADMIN"))):
    return admin_repo.list_modelos()


@router.post("/admin/modelos", status_code=201)
def crear_modelo(datos: ModeloCrear, user: dict = Depends(require_roles("ADMIN"))):
    new_id = admin_repo.create_modelo(
        datos.codigo_modelo,
        datos.nombre,
        datos.categoria,
        datos.descripcion or "",
        datos.comandos_soportados,
        datos.precio_referencia,
        datos.imagen_icono,
    )
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "CREAR_MODELO", f"modelo:{new_id}", "EXITO", datos.nombre)
    return {"id_modelo": new_id, "mensaje": "Modelo comercial registrado"}


@router.put("/admin/modelos/{id_modelo}")
def actualizar_modelo(id_modelo: int, datos: ModeloActualizar, user: dict = Depends(require_roles("ADMIN"))):
    if not admin_repo.get_modelo(id_modelo):
        raise HTTPException(404, "Modelo no encontrado")
    admin_repo.update_modelo(
        id_modelo, datos.nombre, datos.categoria, datos.descripcion or "", datos.comandos_soportados, datos.precio_referencia, datos.activo
    )
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "ACTUALIZAR_MODELO", f"modelo:{id_modelo}", "EXITO", datos.nombre)
    return {"mensaje": "Modelo comercial actualizado"}


# =========================================================================
# CRUD UNIDADES FÍSICAS Y ASIGNACIÓN (SOLO ADMIN)
# =========================================================================
@router.get("/admin/unidades")
def listar_unidades(user: dict = Depends(require_roles("ADMIN"))):
    return admin_repo.list_unidades_admin()


@router.post("/admin/unidades", status_code=201)
def crear_unidad(datos: UnidadCrear, user: dict = Depends(require_roles("ADMIN"))):
    estado = datos.estado_comercial.upper()
    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, f"Estado comercial inválido. Permitidos: {sorted(ESTADOS_VALIDOS)}")
    if datos.id_propietario and not admin_repo.get_user_by_id(datos.id_propietario):
        raise HTTPException(404, "Propietario no encontrado")
    if datos.id_propietario and estado == "DISPONIBLE":
        estado = "VENDIDO"
    try:
        v_id = admin_repo.create_unidad(
            datos.nombre, datos.numero_serie, datos.id_modelo, datos.microcontrolador, datos.descripcion or "", estado, datos.id_propietario
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "CREAR_UNIDAD", f"vehiculo:{v_id}", "EXITO", f"Serie {datos.numero_serie} ({estado})")
    return {"id_vehiculo": v_id, "mensaje": "Unidad registrada con catálogo de comandos del modelo"}


@router.put("/admin/unidades/{id_vehiculo}")
def actualizar_unidad(id_vehiculo: int, datos: UnidadActualizar, user: dict = Depends(require_roles("ADMIN"))):
    unidad = admin_repo.get_unidad(id_vehiculo)
    if not unidad:
        raise HTTPException(404, "Unidad no encontrada")
    estado = datos.estado_comercial.upper()
    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, f"Estado comercial inválido. Permitidos: {sorted(ESTADOS_VALIDOS)}")
    admin_repo.update_unidad(id_vehiculo, datos.nombre, datos.descripcion or "", estado, datos.activo)
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "ACTUALIZAR_UNIDAD", f"vehiculo:{id_vehiculo}", "EXITO", f"Estado={estado}, Activo={datos.activo}")
    return {"mensaje": "Unidad actualizada"}


@router.patch("/admin/unidades/{id_vehiculo}/asignar")
def asignar_unidad(id_vehiculo: int, datos: AsignarUnidadRequest, user: dict = Depends(require_roles("ADMIN"))):
    unidad = admin_repo.get_unidad(id_vehiculo)
    if not unidad:
        raise HTTPException(404, "Unidad no encontrada")
    estado = datos.estado_comercial.upper()
    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, "Estado comercial inválido")
    if datos.id_propietario is not None:
        prop = admin_repo.get_user_by_id(datos.id_propietario)
        if not prop or not prop.get("activo"):
            raise HTTPException(404, "Cliente propietario no encontrado o inactivo")
        detalle = f"Asignado a {prop['correo']} (antes: {unidad.get('propietario_correo') or 'Ninguno'})"
    else:
        detalle = f"Liberado sin propietario (estado: {estado})"

    admin_repo.asignar_propietario(id_vehiculo, datos.id_propietario, estado)
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "ASIGNAR_UNIDAD", f"vehiculo:{id_vehiculo}", "EXITO", detalle)
    return {"mensaje": "Asignación actualizada conservando historial", "detalle": detalle}


@router.delete("/admin/unidades/{id_vehiculo}")
def baja_logica_unidad(id_vehiculo: int, user: dict = Depends(require_roles("ADMIN"))):
    unidad = admin_repo.get_unidad(id_vehiculo)
    if not unidad:
        raise HTTPException(404, "Unidad no encontrada")
    # Regla 7.5: Prohibida eliminación destructiva con historial -> baja lógica
    admin_repo.update_unidad(id_vehiculo, unidad["nombre"], unidad.get("descripcion") or "", "INACTIVO", False)
    invalidar_cache_vehiculo(id_vehiculo)
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "BAJA_LOGICA_UNIDAD", f"vehiculo:{id_vehiculo}", "EXITO", "Desactivada conservando historial")
    return {"mensaje": "Unidad dada de baja lógicamente (historial preservado)"}


@router.get("/admin/unidades/{id_vehiculo}/comandos")
def listar_comandos_unidad(id_vehiculo: int, user: dict = Depends(require_roles("ADMIN"))):
    unidad = admin_repo.get_unidad(id_vehiculo)
    if not unidad:
        raise HTTPException(404, "Unidad no encontrada")
    return {
        "id_vehiculo": id_vehiculo,
        "nombre": unidad["nombre"],
        "comandos": admin_repo.list_comandos_unidad_admin(id_vehiculo),
    }


@router.put("/admin/unidades/{id_vehiculo}/comandos")
def actualizar_comandos_unidad(id_vehiculo: int, datos: ComandosUnidadActualizar, user: dict = Depends(require_roles("ADMIN"))):
    unidad = admin_repo.get_unidad(id_vehiculo)
    if not unidad:
        raise HTTPException(404, "Unidad no encontrada")
    habilitados = admin_repo.actualizar_comandos_unidad(id_vehiculo, datos.codigos_habilitados)
    invalidar_cache_vehiculo(id_vehiculo)
    admin_repo.auditar(
        user["id_usuario"],
        user["correo"],
        user["rol"],
        "ACTUALIZAR_COMANDOS_UNIDAD",
        f"vehiculo:{id_vehiculo}",
        "EXITO",
        f"Comandos habilitados: {','.join(map(str, habilitados))}",
    )
    return {
        "mensaje": "Comandos de la unidad actualizados correctamente",
        "id_vehiculo": id_vehiculo,
        "codigos_habilitados": habilitados,
    }


# =========================================================================
# CRUD CLIENTES Y USUARIOS (SOLO ADMIN)
# =========================================================================
@router.get("/admin/clientes")
def listar_clientes(user: dict = Depends(require_roles("ADMIN"))):
    return admin_repo.list_users()


@router.post("/admin/clientes", status_code=201)
def crear_cliente(datos: ClienteCrear, user: dict = Depends(require_roles("ADMIN"))):
    rol = datos.rol_codigo.upper()
    if rol not in {"ADMIN", "USUARIO", "INVITADO"}:
        raise HTTPException(400, "Rol inválido (ADMIN, USUARIO o INVITADO)")
    if admin_repo.get_user_by_email(datos.correo):
        raise HTTPException(409, "Ya existe una cuenta registrada con ese correo")
    uid = admin_repo.create_user(rol, datos.nombre_completo, datos.correo, hash_password(datos.password), datos.telefono)
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "CREAR_USUARIO", f"usuario:{uid}", "EXITO", f"{datos.correo} ({rol})")
    return {"id_usuario": uid, "mensaje": "Cuenta creada correctamente"}


@router.put("/admin/clientes/{id_usuario}")
def actualizar_cliente(id_usuario: int, datos: ClienteActualizar, user: dict = Depends(require_roles("ADMIN"))):
    if not admin_repo.get_user_by_id(id_usuario):
        raise HTTPException(404, "Usuario no encontrado")
    admin_repo.update_user(id_usuario, datos.nombre_completo, datos.telefono, datos.activo, datos.rol_codigo)
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "ACTUALIZAR_USUARIO", f"usuario:{id_usuario}", "EXITO", f"Activo={datos.activo}, Rol={datos.rol_codigo}")
    return {"mensaje": "Usuario actualizado"}


# =========================================================================
# AUDITORÍA (SOLO ADMIN)
# =========================================================================
@router.get("/admin/auditoria")
def listar_auditoria(limit: int = 50, user: dict = Depends(require_roles("ADMIN"))):
    return admin_repo.list_auditoria(min(max(limit, 1), 200))


# =========================================================================
# MIS VEHÍCULOS (USUARIO Y ADMIN) + CONSENTIMIENTO DE SOPORTE
# =========================================================================
@router.get("/mis-vehiculos")
def mis_vehiculos(user: dict = Depends(require_roles("ADMIN", "USUARIO"))):
    return admin_repo.list_mis_vehiculos(user["id_usuario"], user["rol"])


@router.patch("/mis-vehiculos/{id_vehiculo}/soporte")
def autorizar_soporte(id_vehiculo: int, datos: SoporteAutorizarRequest, user: dict = Depends(require_roles("USUARIO"))):
    unidad = admin_repo.get_unidad(id_vehiculo)
    if not unidad or unidad.get("id_propietario") != user["id_usuario"]:
        raise HTTPException(403, "Solo el propietario de la unidad puede autorizar o revocar soporte técnico")
    admin_repo.set_soporte_autorizado(id_vehiculo, datos.autorizado)
    estado_txt = "AUTORIZADO" if datos.autorizado else "REVOCADO"
    admin_repo.auditar(user["id_usuario"], user["correo"], user["rol"], "SOPORTE_TECNICO", f"vehiculo:{id_vehiculo}", "EXITO", f"Soporte remoto {estado_txt}")
    return {"mensaje": f"Soporte técnico {estado_txt.lower()} para la unidad #{id_vehiculo}", "soporte_autorizado": datos.autorizado}
