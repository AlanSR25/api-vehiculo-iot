import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.schemas import EstadoActualizar, MovimientoIndividual
from app.repositories.sp_repository import sp_repo
from app.services.demo_runner import demo_runner
from app.websocket.connection_manager import ws_manager

router = APIRouter(tags=["Estado e historial"])

# Secuencia en memoria RAM para reproducción rápida (botón 8)
secuencias_usuario: dict[int, list[dict]] = {}
secuencias_reproduciendo: dict[int, asyncio.Task] = {}


async def _reproducir_secuencia_en_ram(vehiculo_id: int, pasos: list[dict]):
    try:
        await ws_manager.broadcast_to_vehiculo(vehiculo_id, {
            "evento": "SECUENCIA_INICIADA",
            "id_vehiculo": vehiculo_id,
            "total_pasos": len(pasos),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        for orden, p in enumerate(pasos, start=1):
            await ws_manager.broadcast_to_vehiculo(vehiculo_id, {
                "evento": "MOVIMIENTO_INDIVIDUAL",
                "id_vehiculo": vehiculo_id,
                "codigo": p["codigo"],
                "comando": p["comando"],
                "orden": orden,
                "total": len(pasos),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await asyncio.sleep(2.0)

        # Al terminar enviar detener (9)
        await ws_manager.broadcast_to_vehiculo(vehiculo_id, {
            "evento": "MOVIMIENTO_INDIVIDUAL",
            "id_vehiculo": vehiculo_id,
            "codigo": 9,
            "comando": "DETENER",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await ws_manager.broadcast_to_vehiculo(vehiculo_id, {
            "evento": "SECUENCIA_FINALIZADA",
            "id_vehiculo": vehiculo_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        secuencias_reproduciendo.pop(vehiculo_id, None)


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

    # Priorizar 'comando' si viene informado; si no, usar 'id_comando' (ignorando 0 de Swagger)
    if datos.comando is not None and str(datos.comando).strip() != "":
        valor = datos.comando
    elif datos.id_comando is not None and datos.id_comando != 0:
        valor = datos.id_comando
    elif datos.id_comando is not None:
        valor = datos.id_comando
    else:
        valor = None

    if valor is None or valor == 0:
        raise HTTPException(422, "Debe especificar 'id_comando' o 'comando' (ej: 1, 'W' o 'AVANZAR')")

    alias_teclas = {
        "W": "AVANZAR",
        "S": "RETROCEDER",
        "A": "GIRAR_IZQUIERDA",
        "D": "GIRAR_DERECHA",
        "U": "SUBIR_BRAZO",
        "J": "BAJAR_BRAZO",
        "L": "LUCES",
        "B": "LUCES",
        "Q": "DETENER",
    }

    comando = None
    # 1. Si es entero o string numérico, buscar por id_comando o codigo
    if isinstance(valor, int) or (isinstance(valor, str) and valor.strip().isdigit()):
        val_int = int(valor)
        comando = next((c for c in comandos if (c["id_comando"] == val_int or c.get("codigo") == val_int) and c.get("activo")), None)

    # 2. Si es string o no se encontró, buscar por alias de tecla o por nombre
    if not comando and isinstance(valor, str):
        val_upper = valor.strip().upper()
        nombre_buscar = alias_teclas.get(val_upper, val_upper)
        comando = next(
            (c for c in comandos if (c["nombre"].upper() == nombre_buscar or c["nombre"].upper() == val_upper) and c.get("activo")),
            None
        )

    if not comando:
        raise HTTPException(400, f"Comando '{valor}' inválido o no pertenece a este vehículo (usa números del 1 al 9)")

    # =========================================================================
    # BOTÓN 8: RECORD & PLAYBACK VOLÁTIL (GRABA EN MEMORIA Y AL 2DO 8 REPRODUCE)
    # NO TOCA LA TABLA DEMOS NI DEMO_MOVIMIENTOS DE LA BASE DE DATOS
    # =========================================================================
    if comando.get("codigo") == 8 or "GRABAR" in comando.get("nombre", "") or comando.get("nombre") == "DEMO":
        # 1. Si no estaba grabando: INICIAR GRABACIÓN
        if id_vehiculo not in secuencias_usuario:
            # Si estaba reproduciendo una previa, cancelarla
            if id_vehiculo in secuencias_reproduciendo:
                secuencias_reproduciendo[id_vehiculo].cancel()
                secuencias_reproduciendo.pop(id_vehiculo, None)

            secuencias_usuario[id_vehiculo] = []
            await ws_manager.broadcast_to_vehiculo(id_vehiculo, {
                "evento": "GRABACION_INICIADA",
                "id_vehiculo": id_vehiculo,
                "codigo": 8,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {
                "resultado": "GRABACION_INICIADA",
                "id_vehiculo": id_vehiculo,
                "codigo": 8,
                "estado": "GRABANDO",
                "mensaje": "[MODO GRABACION] Grabacion iniciada. Mueve tu carrito (1, 2, 3...). Al pulsar 8 de nuevo ejecutara la secuencia grabada."
            }
        else:
            # 2. Si ya estaba grabando: FINALIZAR Y REPRODUCIR LA SECUENCIA EN RAM
            pasos = list(secuencias_usuario.pop(id_vehiculo))
            if pasos:
                # Cancelar si hubiera alguna corriendo
                if id_vehiculo in secuencias_reproduciendo:
                    secuencias_reproduciendo[id_vehiculo].cancel()
                task = asyncio.create_task(_reproducir_secuencia_en_ram(id_vehiculo, pasos))
                secuencias_reproduciendo[id_vehiculo] = task

            return {
                "resultado": "REPRODUCIENDO_SECUENCIA",
                "id_vehiculo": id_vehiculo,
                "codigo": 8,
                "estado": "REPRODUCIENDO",
                "total_movimientos": len(pasos),
                "mensaje": f"[REPRODUCIENDO] Ejecutando los {len(pasos)} movimientos que grabaste."
            }

    # =========================================================================
    # BOTÓN 9 (DETENER): DETIENE REPRODUCCIÓN O DEMOS
    # =========================================================================
    if comando.get("codigo") == 9 or comando.get("nombre") == "DETENER":
        if id_vehiculo in secuencias_reproduciendo:
            secuencias_reproduciendo[id_vehiculo].cancel()
            secuencias_reproduciendo.pop(id_vehiculo, None)
        if demo_runner.is_running(id_vehiculo):
            demo_runner.cancel_demo(id_vehiculo)

    # Si estamos en modo grabación, guardar el movimiento en memoria RAM
    grabacion_info = None
    if id_vehiculo in secuencias_usuario:
        secuencias_usuario[id_vehiculo].append({
            "codigo": comando["codigo"],
            "comando": comando["nombre"],
            "id_comando": comando["id_comando"]
        })
        paso_num = len(secuencias_usuario[id_vehiculo])
        grabacion_info = f"Paso {paso_num} grabado en memoria (pulsa 8 para reproducir la secuencia)"

    id_comando_final = comando["id_comando"]

    # 1. EMITIR INMEDIATAMENTE POR WEBSOCKET (CERO LATENCIA PARA EL ESP32)
    await ws_manager.broadcast_to_vehiculo(id_vehiculo, {
        "evento": "MOVIMIENTO_INDIVIDUAL",
        "id_vehiculo": id_vehiculo,
        "codigo": comando["codigo"],
        "comando": comando["nombre"],
        "origen": datos.origen,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # 2. Persistir en RDS MySQL en segundo plano
    await asyncio.to_thread(sp_repo.ejecutar_movimiento_individual_tx, id_vehiculo, id_comando_final, True, datos.origen)
    resp = {
        "resultado": "EXITO",
        "id_vehiculo": id_vehiculo,
        "codigo": comando["codigo"],
        "comando": comando["nombre"],
        "descripcion": comando.get("descripcion", "")
    }
    if grabacion_info:
        resp["grabacion"] = grabacion_info
    return resp

