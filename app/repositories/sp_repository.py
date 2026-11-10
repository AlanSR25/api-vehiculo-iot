from app.core.database import db_manager


class StoredProcedureRepository:
    def _execute(self, sp_name: str, args: tuple = (), write: bool = False):
        connection = db_manager.get_connection()
        cursor = connection.cursor(dictionary=True)
        results = []
        try:
            cursor.callproc(sp_name, args)
            for result in cursor.stored_results():
                results.extend(result.fetchall())
            if write:
                connection.commit()
            return results
        except Exception:
            if write:
                connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def _read(self, name, args=()): return self._execute(name, args)
    def _write(self, name, args=()): return self._execute(name, args, True)

    def sp_crear_vehiculo(self, n, m, d, mc): return self._write("sp_crear_vehiculo", (n, m, d, mc))
    def sp_obtener_vehiculos(self): return self._read("sp_obtener_vehiculos")
    def sp_obtener_vehiculo(self, v_id): return self._read("sp_obtener_vehiculo", (v_id,))
    def sp_actualizar_vehiculo(self, v_id, n, m, d, mc, act): return self._write("sp_actualizar_vehiculo", (v_id, n, m, d, mc, act))
    def sp_eliminar_vehiculo(self, v_id): return self._write("sp_eliminar_vehiculo", (v_id,))
    def sp_crear_comando(self, v_id, n, c, d): return self._write("sp_crear_comando", (v_id, n, c, d))
    def sp_obtener_comandos_vehiculo(self, v_id): return self._read("sp_obtener_comandos_vehiculo", (v_id,))
    def sp_actualizar_comando(self, c_id, n, c, d, act): return self._write("sp_actualizar_comando", (c_id, n, c, d, act))
    def sp_eliminar_comando(self, c_id): return self._write("sp_eliminar_comando", (c_id,))
    def sp_actualizar_estado(self, v_id, c_id, con): return self._write("sp_actualizar_estado", (v_id, c_id, con))
    def sp_obtener_estado(self, v_id): return self._read("sp_obtener_estado", (v_id,))
    def sp_registrar_historial(self, v_id, c_id, orig): return self._write("sp_registrar_historial", (v_id, c_id, orig))
    def sp_obtener_historial(self, v_id): return self._read("sp_obtener_historial", (v_id,))
    def sp_crear_demo(self, v_id, n, d): return self._write("sp_crear_demo", (v_id, n, d))
    def sp_obtener_demos(self, v_id): return self._read("sp_obtener_demos", (v_id,))
    def sp_actualizar_demo(self, d_id, n, d, act): return self._write("sp_actualizar_demo", (d_id, n, d, act))
    def sp_eliminar_demo(self, d_id): return self._write("sp_eliminar_demo", (d_id,))
    def sp_agregar_movimiento_demo(self, d_id, c_id, orden, dur, pausa): return self._write("sp_agregar_movimiento_demo", (d_id, c_id, orden, dur, pausa))
    def sp_obtener_movimientos_demo(self, d_id): return self._read("sp_obtener_movimientos_demo", (d_id,))
    def sp_actualizar_movimiento_demo(self, m_id, c_id, orden, dur, pausa): return self._write("sp_actualizar_movimiento_demo", (m_id, c_id, orden, dur, pausa))
    def sp_eliminar_movimiento_demo(self, m_id): return self._write("sp_eliminar_movimiento_demo", (m_id,))

    def limpiar_movimientos_demo(self, d_id: int):
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM demo_movimientos WHERE id_demo = %s", (d_id,))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def ejecutar_movimiento_individual_tx(self, v_id, c_id, conectado, origen):
        connection = db_manager.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.callproc("sp_actualizar_estado", (v_id, c_id, conectado))
            list(cursor.stored_results())
            cursor.callproc("sp_registrar_historial", (v_id, c_id, origen))
            list(cursor.stored_results())
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()


sp_repo = StoredProcedureRepository()

