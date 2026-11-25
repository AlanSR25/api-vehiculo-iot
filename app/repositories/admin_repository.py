"""
admin_repository.py - Acceso parametrizado a Amazon RDS MySQL para la plataforma 4.3:
Usuarios, Roles, Modelos Comerciales, Unidades, Asignaciones, Demos, Sesiones Invitado y Auditoría.
"""
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import db_manager


class AdminRepository:
    def _query(self, sql: str, params: tuple = (), one: bool = False):
        conn = db_manager.get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.fetchone() if one else cur.fetchall()
        finally:
            cur.close()
            conn.close()

    def _execute(self, sql: str, params: tuple = ()) -> int:
        conn = db_manager.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    # =========================================================================
    # AUDITORÍA
    # =========================================================================
    def auditar(
        self,
        id_usuario: Optional[int],
        actor_correo: Optional[str],
        actor_rol: Optional[str],
        accion: str,
        recurso: str,
        resultado: str = "EXITO",
        detalle: Optional[str] = None,
    ) -> None:
        try:
            self._execute(
                """
                INSERT INTO auditoria (id_usuario, actor_correo, actor_rol, accion, recurso, resultado, detalle)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (id_usuario, actor_correo, actor_rol, accion[:80], recurso[:100], resultado[:30], (detalle or "")[:255]),
            )
        except Exception:
            pass

    def list_auditoria(self, limit: int = 50):
        return self._query(
            """
            SELECT id_auditoria, id_usuario, actor_correo, actor_rol, accion, recurso, resultado, detalle, fecha_hora
            FROM auditoria
            ORDER BY id_auditoria DESC
            LIMIT %s
            """,
            (limit,),
        )

    # =========================================================================
    # USUARIOS Y ROLES
    # =========================================================================
    def get_user_by_email(self, correo: str):
        return self._query(
            """
            SELECT u.id_usuario, u.nombre_completo, u.correo, u.password_hash, u.telefono, u.activo,
                   u.fecha_creacion, r.id_rol, r.codigo AS rol_codigo, r.nombre AS rol_nombre
            FROM usuarios u
            JOIN roles r ON r.id_rol = u.id_rol
            WHERE u.correo = %s
            """,
            (correo.strip().lower(),),
            one=True,
        )

    def get_user_by_id(self, id_usuario: int):
        return self._query(
            """
            SELECT u.id_usuario, u.nombre_completo, u.correo, u.telefono, u.activo,
                   u.fecha_creacion, r.id_rol, r.codigo AS rol_codigo, r.nombre AS rol_nombre
            FROM usuarios u
            JOIN roles r ON r.id_rol = u.id_rol
            WHERE u.id_usuario = %s
            """,
            (id_usuario,),
            one=True,
        )

    def list_users(self):
        return self._query(
            """
            SELECT u.id_usuario, u.nombre_completo, u.correo, u.telefono, u.activo, u.fecha_creacion,
                   r.codigo AS rol_codigo, r.nombre AS rol_nombre,
                   (SELECT COUNT(*) FROM vehiculos v WHERE v.id_propietario = u.id_usuario AND v.activo = 1) AS total_unidades
            FROM usuarios u
            JOIN roles r ON r.id_rol = u.id_rol
            ORDER BY u.id_usuario ASC
            """
        )

    def get_rol_by_codigo(self, codigo: str):
        return self._query("SELECT * FROM roles WHERE codigo = %s", (codigo.upper(),), one=True)

    def create_user(self, rol_codigo: str, nombre: str, correo: str, password_hash: str, telefono: Optional[str]):
        rol = self.get_rol_by_codigo(rol_codigo)
        if not rol:
            raise ValueError(f"Rol '{rol_codigo}' no existe")
        return self._execute(
            """
            INSERT INTO usuarios (id_rol, nombre_completo, correo, password_hash, telefono, activo)
            VALUES (%s, %s, %s, %s, %s, 1)
            """,
            (rol["id_rol"], nombre.strip(), correo.strip().lower(), password_hash, telefono),
        )

    def update_user(self, id_usuario: int, nombre: str, telefono: Optional[str], activo: bool, rol_codigo: Optional[str] = None):
        if rol_codigo:
            rol = self.get_rol_by_codigo(rol_codigo)
            if not rol:
                raise ValueError("Rol inválido")
            self._execute(
                "UPDATE usuarios SET nombre_completo=%s, telefono=%s, activo=%s, id_rol=%s WHERE id_usuario=%s",
                (nombre.strip(), telefono, int(activo), rol["id_rol"], id_usuario),
            )
        else:
            self._execute(
                "UPDATE usuarios SET nombre_completo=%s, telefono=%s, activo=%s WHERE id_usuario=%s",
                (nombre.strip(), telefono, int(activo), id_usuario),
            )

    # =========================================================================
    # MODELOS COMERCIALES
    # =========================================================================
    def list_modelos(self, solo_activos: bool = False):
        where = "WHERE m.activo = 1" if solo_activos else ""
        return self._query(
            f"""
            SELECT m.*,
                   (SELECT COUNT(*) FROM vehiculos v WHERE v.id_modelo = m.id_modelo AND v.activo = 1) AS total_unidades,
                   (SELECT COUNT(*) FROM vehiculos v WHERE v.id_modelo = m.id_modelo AND v.activo = 1 AND v.estado_comercial = 'EXHIBICION') AS unidades_exhibicion
            FROM modelos_comerciales m
            {where}
            ORDER BY m.id_modelo ASC
            """
        )

    def get_modelo(self, id_modelo: int):
        return self._query("SELECT * FROM modelos_comerciales WHERE id_modelo = %s", (id_modelo,), one=True)

    def create_modelo(self, codigo_modelo: str, nombre: str, categoria: str, descripcion: str, comandos_soportados: str, precio: float, imagen_icono: str):
        return self._execute(
            """
            INSERT INTO modelos_comerciales (codigo_modelo, nombre, categoria, descripcion, comandos_soportados, precio_referencia, imagen_icono, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
            """,
            (codigo_modelo.strip().upper(), nombre.strip(), categoria.strip(), descripcion, comandos_soportados, precio, imagen_icono),
        )

    def update_modelo(self, id_modelo: int, nombre: str, categoria: str, descripcion: str, comandos_soportados: str, precio: float, activo: bool):
        self._execute(
            """
            UPDATE modelos_comerciales
            SET nombre=%s, categoria=%s, descripcion=%s, comandos_soportados=%s, precio_referencia=%s, activo=%s
            WHERE id_modelo=%s
            """,
            (nombre.strip(), categoria.strip(), descripcion, comandos_soportados, precio, int(activo), id_modelo),
        )

    # =========================================================================
    # UNIDADES FÍSICAS (VEHÍCULOS EXTENDIDOS)
    # =========================================================================
    def list_unidades_admin(self):
        return self._query(
            """
            SELECT v.id_vehiculo, v.numero_serie, v.nombre, v.modelo, v.descripcion, v.microcontrolador,
                   v.estado_comercial, v.soporte_autorizado, v.activo, v.fecha_registro,
                   v.id_modelo, m.nombre AS modelo_comercial_nombre, m.codigo_modelo, m.comandos_soportados,
                   v.id_propietario, u.nombre_completo AS propietario_nombre, u.correo AS propietario_correo,
                   (SELECT COUNT(*) FROM historial_comandos h WHERE h.id_vehiculo = v.id_vehiculo) AS total_historial
            FROM vehiculos v
            LEFT JOIN modelos_comerciales m ON m.id_modelo = v.id_modelo
            LEFT JOIN usuarios u ON u.id_usuario = v.id_propietario
            ORDER BY v.id_vehiculo ASC
            """
        )

    def get_unidad(self, id_vehiculo: int):
        return self._query(
            """
            SELECT v.id_vehiculo, v.numero_serie, v.nombre, v.modelo, v.descripcion, v.microcontrolador,
                   v.estado_comercial, v.soporte_autorizado, v.activo, v.fecha_registro,
                   v.id_modelo, m.nombre AS modelo_comercial_nombre, m.comandos_soportados,
                   v.id_propietario, u.nombre_completo AS propietario_nombre, u.correo AS propietario_correo
            FROM vehiculos v
            LEFT JOIN modelos_comerciales m ON m.id_modelo = v.id_modelo
            LEFT JOIN usuarios u ON u.id_usuario = v.id_propietario
            WHERE v.id_vehiculo = %s
            """,
            (id_vehiculo,),
            one=True,
        )

    def list_mis_vehiculos(self, id_usuario: int, rol: str):
        if rol == "ADMIN":
            return self.list_unidades_admin()
        return self._query(
            """
            SELECT v.id_vehiculo, v.numero_serie, v.nombre, v.modelo, v.descripcion, v.microcontrolador,
                   v.estado_comercial, v.soporte_autorizado, v.activo, v.id_modelo,
                   m.nombre AS modelo_comercial_nombre, m.comandos_soportados
            FROM vehiculos v
            LEFT JOIN modelos_comerciales m ON m.id_modelo = v.id_modelo
            WHERE v.id_propietario = %s AND v.activo = 1
            ORDER BY v.id_vehiculo ASC
            """,
            (id_usuario,),
        )

    def create_unidad(
        self,
        nombre: str,
        numero_serie: str,
        id_modelo: int,
        microcontrolador: str,
        descripcion: str,
        estado_comercial: str,
        id_propietario: Optional[int],
    ) -> int:
        modelo = self.get_modelo(id_modelo)
        if not modelo:
            raise ValueError("Modelo comercial no encontrado")
        conn = db_manager.get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """
                INSERT INTO vehiculos (nombre, modelo, descripcion, microcontrolador, activo, numero_serie, id_modelo, id_propietario, estado_comercial)
                VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s)
                """,
                (nombre.strip(), modelo["nombre"], descripcion, microcontrolador, numero_serie.strip().upper(), id_modelo, id_propietario, estado_comercial),
            )
            v_id = cur.lastrowid

            # Crear los comandos soportados por el modelo comercial
            catalogo = {
                1: ("AVANZAR", "Avanzar"),
                2: ("RETROCEDER", "Retroceder"),
                3: ("GIRAR_IZQUIERDA", "Girar Izquierda"),
                4: ("GIRAR_DERECHA", "Girar Derecha"),
                5: ("SUBIR_BRAZO", "Subir Brazo"),
                6: ("BAJAR_BRAZO", "Bajar Brazo"),
                7: ("LUZ", "Luces On/Off"),
                8: ("GRABAR_SECUENCIA", "Grabar/Reproducir secuencia RAM"),
                9: ("DETENER", "Detener / Parada segura"),
            }
            soportados = [int(x.strip()) for x in str(modelo.get("comandos_soportados", "1,2,3,4,7,9")).split(",") if x.strip().isdigit()]
            if 9 not in soportados:
                soportados.append(9)

            cmd_detener_id = None
            for cod in sorted(set(soportados)):
                if cod in catalogo:
                    nom, desc = catalogo[cod]
                    cur.execute(
                        "INSERT INTO comandos (id_vehiculo, nombre, codigo, descripcion, activo) VALUES (%s, %s, %s, %s, 1)",
                        (v_id, nom, cod, desc),
                    )
                    if cod == 9:
                        cmd_detener_id = cur.lastrowid

            cur.execute(
                "INSERT INTO estado_vehiculo (id_vehiculo, id_comando, conectado) VALUES (%s, %s, 0)",
                (v_id, cmd_detener_id),
            )
            conn.commit()
            return v_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def update_unidad(self, id_vehiculo: int, nombre: str, descripcion: str, estado_comercial: str, activo: bool):
        self._execute(
            "UPDATE vehiculos SET nombre=%s, descripcion=%s, estado_comercial=%s, activo=%s WHERE id_vehiculo=%s",
            (nombre.strip(), descripcion, estado_comercial, int(activo), id_vehiculo),
        )

    def asignar_propietario(self, id_vehiculo: int, id_propietario: Optional[int], estado_comercial: str):
        self._execute(
            "UPDATE vehiculos SET id_propietario=%s, estado_comercial=%s, soporte_autorizado=0 WHERE id_vehiculo=%s",
            (id_propietario, estado_comercial, id_vehiculo),
        )

    def set_soporte_autorizado(self, id_vehiculo: int, autorizado: bool):
        self._execute("UPDATE vehiculos SET soporte_autorizado=%s WHERE id_vehiculo=%s", (int(autorizado), id_vehiculo))

    def list_comandos_unidad_admin(self, id_vehiculo: int):
        catalogo = {
            1: ("AVANZAR", "Avanzar"),
            2: ("RETROCEDER", "Retroceder"),
            3: ("GIRAR_IZQUIERDA", "Girar Izquierda"),
            4: ("GIRAR_DERECHA", "Girar Derecha"),
            5: ("SUBIR_BRAZO", "Subir Brazo"),
            6: ("BAJAR_BRAZO", "Bajar Brazo"),
            7: ("LUZ", "Luces On/Off"),
            8: ("GRABAR_SECUENCIA", "Grabar/Reproducir secuencia RAM"),
            9: ("DETENER", "Detener / Parada segura"),
        }
        existentes = self._query(
            "SELECT id_comando, codigo, nombre, descripcion, activo FROM comandos WHERE id_vehiculo = %s ORDER BY codigo ASC",
            (id_vehiculo,),
        )
        por_codigo = {int(c["codigo"]): c for c in existentes if c.get("codigo") is not None}
        resultado = []
        for cod in range(1, 10):
            if cod in por_codigo:
                c = por_codigo[cod]
                resultado.append({
                    "id_comando": c["id_comando"],
                    "codigo": cod,
                    "nombre": c["nombre"],
                    "descripcion": c.get("descripcion") or catalogo[cod][1],
                    "activo": bool(c.get("activo")),
                })
            else:
                resultado.append({
                    "id_comando": None,
                    "codigo": cod,
                    "nombre": catalogo[cod][0],
                    "descripcion": catalogo[cod][1],
                    "activo": False,
                })
        return resultado

    def actualizar_comandos_unidad(self, id_vehiculo: int, codigos_habilitados: list[int]):
        catalogo = {
            1: ("AVANZAR", "Avanzar"),
            2: ("RETROCEDER", "Retroceder"),
            3: ("GIRAR_IZQUIERDA", "Girar Izquierda"),
            4: ("GIRAR_DERECHA", "Girar Derecha"),
            5: ("SUBIR_BRAZO", "Subir Brazo"),
            6: ("BAJAR_BRAZO", "Bajar Brazo"),
            7: ("LUZ", "Luces On/Off"),
            8: ("GRABAR_SECUENCIA", "Grabar/Reproducir secuencia RAM"),
            9: ("DETENER", "Detener / Parada segura"),
        }
        habilitados = {int(c) for c in codigos_habilitados if 1 <= int(c) <= 9}
        # Regla de seguridad física: DETENER (9) siempre debe permanecer activo
        habilitados.add(9)

        conn = db_manager.get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT id_comando, codigo FROM comandos WHERE id_vehiculo = %s", (id_vehiculo,))
            existentes = {int(r["codigo"]): r["id_comando"] for r in cur.fetchall() if r.get("codigo") is not None}

            for cod in range(1, 10):
                activo = 1 if cod in habilitados else 0
                if cod in existentes:
                    cur.execute("UPDATE comandos SET activo = %s WHERE id_comando = %s", (activo, existentes[cod]))
                elif activo == 1:
                    nom, desc = catalogo[cod]
                    cur.execute(
                        "INSERT INTO comandos (id_vehiculo, nombre, codigo, descripcion, activo) VALUES (%s, %s, %s, %s, 1)",
                        (id_vehiculo, nom, cod, desc),
                    )
            conn.commit()
            return sorted(habilitados)
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    # =========================================================================
    # DASHBOARD METRICAS REALES
    # =========================================================================
    def get_dashboard_metrics(self):
        return self._query(
            """
            SELECT
                (SELECT COUNT(*) FROM modelos_comerciales WHERE activo = 1) AS total_modelos,
                (SELECT COUNT(*) FROM vehiculos WHERE activo = 1) AS total_unidades,
                (SELECT COUNT(*) FROM vehiculos WHERE activo = 1 AND estado_comercial = 'VENDIDO') AS unidades_vendidas,
                (SELECT COUNT(*) FROM vehiculos WHERE activo = 1 AND estado_comercial = 'EXHIBICION') AS unidades_exhibicion,
                (SELECT COUNT(*) FROM vehiculos WHERE activo = 1 AND estado_comercial = 'DISPONIBLE') AS unidades_disponibles,
                (SELECT COUNT(*) FROM usuarios u JOIN roles r ON r.id_rol=u.id_rol WHERE r.codigo='USUARIO' AND u.activo=1) AS total_clientes,
                (SELECT COUNT(*) FROM demos WHERE activo = 1) AS total_demos,
                (SELECT COUNT(*) FROM historial_comandos) AS total_movimientos_historicos,
                (SELECT COUNT(*) FROM sesiones_invitado WHERE activa = 1 AND fecha_expiracion > UTC_TIMESTAMP()) AS sesiones_invitado_activas
            """,
            one=True,
        )

    # =========================================================================
    # EDITOR DE DEMOS (CON PASOS ORDENADOS)
    # =========================================================================
    def list_demos_con_pasos(self, id_vehiculo: int, user: dict):
        rol = user.get("rol")
        uid = user.get("id_usuario")
        if rol == "ADMIN":
            demos = self._query(
                "SELECT * FROM demos WHERE id_vehiculo = %s AND activo = 1 ORDER BY tipo_demo ASC, id_demo ASC",
                (id_vehiculo,),
            )
        else:
            demos = self._query(
                """
                SELECT * FROM demos
                WHERE id_vehiculo = %s AND activo = 1
                  AND (tipo_demo = 'FABRICA' OR id_usuario = %s)
                ORDER BY tipo_demo ASC, id_demo ASC
                """,
                (id_vehiculo, uid),
            )
        for d in demos:
            d["pasos"] = self._query(
                """
                SELECT dm.id_demo_movimiento, dm.id_comando, dm.orden, dm.duracion_ms, dm.pausa_ms,
                       c.nombre AS comando, c.codigo
                FROM demo_movimientos dm
                JOIN comandos c ON c.id_comando = dm.id_comando
                WHERE dm.id_demo = %s
                ORDER BY dm.orden ASC
                """,
                (d["id_demo"],),
            )
            d["duracion_total_ms"] = sum(int(p["duracion_ms"]) + int(p["pausa_ms"]) for p in d["pasos"])
        return demos

    def get_demo(self, id_demo: int):
        return self._query("SELECT * FROM demos WHERE id_demo = %s", (id_demo,), one=True)

    def save_demo_completa(
        self,
        id_vehiculo: int,
        nombre: str,
        descripcion: str,
        id_usuario: Optional[int],
        tipo_demo: str,
        pasos: list[dict],
        id_demo_editar: Optional[int] = None,
    ) -> int:
        conn = db_manager.get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            if id_demo_editar:
                cur.execute(
                    "UPDATE demos SET nombre=%s, descripcion=%s WHERE id_demo=%s",
                    (nombre.strip(), descripcion, id_demo_editar),
                )
                cur.execute("DELETE FROM demo_movimientos WHERE id_demo=%s", (id_demo_editar,))
                demo_id = id_demo_editar
            else:
                cur.execute(
                    "INSERT INTO demos (id_vehiculo, nombre, descripcion, activo, id_usuario, tipo_demo) VALUES (%s, %s, %s, 1, %s, %s)",
                    (id_vehiculo, nombre.strip(), descripcion, id_usuario, tipo_demo),
                )
                demo_id = cur.lastrowid

            for idx, p in enumerate(pasos, start=1):
                cur.execute(
                    """
                    INSERT INTO demo_movimientos (id_demo, id_comando, orden, duracion_ms, pausa_ms)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (demo_id, p["id_comando"], idx, p["duracion_ms"], p.get("pausa_ms", 200)),
                )
            conn.commit()
            return demo_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def delete_demo_logica(self, id_demo: int):
        self._execute("UPDATE demos SET activo = 0 WHERE id_demo = %s", (id_demo,))

    # =========================================================================
    # SESIONES TEMPORALES DE INVITADO (RESERVA EXCLUSIVA)
    # =========================================================================
    def expirar_sesiones_vencidas(self) -> list[dict]:
        vencidas = self._query(
            "SELECT * FROM sesiones_invitado WHERE activa = 1 AND fecha_expiracion <= UTC_TIMESTAMP()"
        )
        if vencidas:
            self._execute(
                "UPDATE sesiones_invitado SET activa = 0, motivo_cierre = 'EXPIRADA' WHERE activa = 1 AND fecha_expiracion <= UTC_TIMESTAMP()"
            )
        return vencidas

    def get_sesion_activa_vehiculo(self, id_vehiculo: int):
        self.expirar_sesiones_vencidas()
        return self._query(
            """
            SELECT *, TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), fecha_expiracion) AS segundos_restantes
            FROM sesiones_invitado
            WHERE id_vehiculo = %s AND activa = 1 AND fecha_expiracion > UTC_TIMESTAMP()
            ORDER BY id_sesion DESC LIMIT 1
            """,
            (id_vehiculo,),
            one=True,
        )

    def get_sesion_por_token(self, token_sesion: str):
        self.expirar_sesiones_vencidas()
        return self._query(
            """
            SELECT *, TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), fecha_expiracion) AS segundos_restantes
            FROM sesiones_invitado
            WHERE token_sesion = %s
            """,
            (token_sesion,),
            one=True,
        )

    def crear_sesion_invitado(
        self,
        id_vehiculo: int,
        nombre_invitado: str,
        token_sesion: str,
        duracion_seg: int,
        id_usuario: Optional[int] = None,
        comandos_permitidos: str = "1,2,3,4,7,9",
    ) -> int:
        now = datetime.utcnow()
        exp = now + timedelta(seconds=duracion_seg)
        return self._execute(
            """
            INSERT INTO sesiones_invitado (id_usuario, id_vehiculo, nombre_invitado, token_sesion, comandos_permitidos, fecha_inicio, fecha_expiracion, activa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
            """,
            (id_usuario, id_vehiculo, nombre_invitado.strip()[:100], token_sesion, comandos_permitidos, now, exp),
        )

    def cerrar_sesion_invitado(self, token_sesion: str, motivo: str = "FINALIZADA_USUARIO"):
        self._execute(
            "UPDATE sesiones_invitado SET activa = 0, motivo_cierre = %s WHERE token_sesion = %s",
            (motivo, token_sesion),
        )

    def list_unidades_exhibicion_publicas(self):
        self.expirar_sesiones_vencidas()
        return self._query(
            """
            SELECT v.id_vehiculo, v.numero_serie, v.nombre, v.modelo, v.descripcion, v.microcontrolador,
                   m.nombre AS modelo_comercial, m.categoria, m.imagen_icono, m.comandos_soportados,
                   s.id_sesion AS sesion_activa_id,
                   s.nombre_invitado AS ocupado_por,
                   GREATEST(0, COALESCE(TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), s.fecha_expiracion), 0)) AS segundos_restantes
            FROM vehiculos v
            LEFT JOIN modelos_comerciales m ON m.id_modelo = v.id_modelo
            LEFT JOIN sesiones_invitado s ON s.id_vehiculo = v.id_vehiculo AND s.activa = 1 AND s.fecha_expiracion > UTC_TIMESTAMP()
            WHERE v.activo = 1 AND v.estado_comercial = 'EXHIBICION'
            ORDER BY v.id_vehiculo ASC
            """
        )


admin_repo = AdminRepository()
