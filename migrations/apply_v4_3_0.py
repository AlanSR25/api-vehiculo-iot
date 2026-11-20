"""
Aplicador idempotente de la migración V4.3.0 para Amazon RDS MySQL (vehiculo_iot).
Preserva al 100% los datos históricos de las prácticas 4.1 y 4.2.
"""
import hashlib
import os
import secrets
from app.core.database import db_manager


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256$100000${salt}${dk.hex()}"


def column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cur.fetchone()["c"] > 0


def fk_exists(cur, table: str, constraint_name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s
        """,
        (table, constraint_name),
    )
    return cur.fetchone()["c"] > 0


def main():
    conn = db_manager.get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # 1. Crear tablas nuevas
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS roles (
                id_rol INT AUTO_INCREMENT PRIMARY KEY,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                nombre VARCHAR(60) NOT NULL,
                descripcion VARCHAR(255) NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                id_rol INT NOT NULL,
                nombre_completo VARCHAR(120) NOT NULL,
                correo VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                telefono VARCHAR(30) NULL,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_usuarios_rol FOREIGN KEY (id_rol) REFERENCES roles(id_rol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS modelos_comerciales (
                id_modelo INT AUTO_INCREMENT PRIMARY KEY,
                codigo_modelo VARCHAR(40) NOT NULL UNIQUE,
                nombre VARCHAR(100) NOT NULL,
                categoria VARCHAR(60) NOT NULL DEFAULT 'Vehículo IoT',
                descripcion VARCHAR(255) NULL,
                comandos_soportados VARCHAR(60) NOT NULL DEFAULT '1,2,3,4,5,6,7,8,9',
                precio_referencia DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                imagen_icono VARCHAR(60) NOT NULL DEFAULT 'bi-truck-front',
                activo TINYINT(1) NOT NULL DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS sesiones_invitado (
                id_sesion INT AUTO_INCREMENT PRIMARY KEY,
                id_usuario INT NULL,
                id_vehiculo INT NOT NULL,
                nombre_invitado VARCHAR(100) NOT NULL DEFAULT 'Visitante',
                token_sesion VARCHAR(128) NOT NULL UNIQUE,
                comandos_permitidos VARCHAR(60) NOT NULL DEFAULT '1,2,3,4,7,9',
                fecha_inicio DATETIME NOT NULL,
                fecha_expiracion DATETIME NOT NULL,
                activa TINYINT(1) NOT NULL DEFAULT 1,
                motivo_cierre VARCHAR(80) NULL,
                INDEX idx_sesion_vehiculo_activa (id_vehiculo, activa),
                CONSTRAINT fk_sesion_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
                CONSTRAINT fk_sesion_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id_vehiculo) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS auditoria (
                id_auditoria INT AUTO_INCREMENT PRIMARY KEY,
                id_usuario INT NULL,
                actor_correo VARCHAR(120) NULL,
                actor_rol VARCHAR(30) NULL,
                accion VARCHAR(80) NOT NULL,
                recurso VARCHAR(100) NOT NULL,
                resultado VARCHAR(30) NOT NULL DEFAULT 'EXITO',
                detalle VARCHAR(255) NULL,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_auditoria_fecha (fecha_hora),
                INDEX idx_auditoria_accion (accion)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
        ]
        for stmt in ddl_statements:
            cur.execute(stmt)

        # 2. Alteraciones incrementales en vehiculos
        vehiculo_cols = [
            ("numero_serie", "ALTER TABLE vehiculos ADD COLUMN numero_serie VARCHAR(60) NULL UNIQUE"),
            ("id_modelo", "ALTER TABLE vehiculos ADD COLUMN id_modelo INT NULL"),
            ("id_propietario", "ALTER TABLE vehiculos ADD COLUMN id_propietario INT NULL"),
            ("estado_comercial", "ALTER TABLE vehiculos ADD COLUMN estado_comercial ENUM('DISPONIBLE','VENDIDO','EXHIBICION','MANTENIMIENTO','INACTIVO') NOT NULL DEFAULT 'EXHIBICION'"),
            ("soporte_autorizado", "ALTER TABLE vehiculos ADD COLUMN soporte_autorizado TINYINT(1) NOT NULL DEFAULT 0"),
        ]
        for col, sql in vehiculo_cols:
            if not column_exists(cur, "vehiculos", col):
                cur.execute(sql)

        if not fk_exists(cur, "vehiculos", "fk_vehiculos_modelo"):
            cur.execute("ALTER TABLE vehiculos ADD CONSTRAINT fk_vehiculos_modelo FOREIGN KEY (id_modelo) REFERENCES modelos_comerciales(id_modelo) ON DELETE SET NULL")
        if not fk_exists(cur, "vehiculos", "fk_vehiculos_propietario"):
            cur.execute("ALTER TABLE vehiculos ADD CONSTRAINT fk_vehiculos_propietario FOREIGN KEY (id_propietario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL")

        # 3. Alteraciones incrementales en demos
        demo_cols = [
            ("id_usuario", "ALTER TABLE demos ADD COLUMN id_usuario INT NULL"),
            ("tipo_demo", "ALTER TABLE demos ADD COLUMN tipo_demo ENUM('FABRICA','PRIVADA') NOT NULL DEFAULT 'FABRICA'"),
        ]
        for col, sql in demo_cols:
            if not column_exists(cur, "demos", col):
                cur.execute(sql)

        if not fk_exists(cur, "demos", "fk_demos_usuario"):
            cur.execute("ALTER TABLE demos ADD CONSTRAINT fk_demos_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL")

        # 4. Seed Roles
        cur.execute(
            """
            INSERT IGNORE INTO roles (codigo, nombre, descripcion) VALUES
            ('ADMIN', 'Administrador', 'Empresa comercializadora: inventario, clientes, asignaciones, demos de fábrica y auditoría'),
            ('USUARIO', 'Usuario Comprador', 'Cliente propietario: controla y monitorea únicamente sus unidades y gestiona sus demos privadas'),
            ('INVITADO', 'Invitado / Prospecto', 'Cliente potencial: explora catálogo público y solicita sesión temporal limitada de exhibición')
            """
        )

        # 5. Seed Modelos Comerciales
        cur.execute(
            """
            INSERT IGNORE INTO modelos_comerciales (codigo_modelo, nombre, categoria, descripcion, comandos_soportados, precio_referencia, imagen_icono) VALUES
            ('MOD-EXC-01', 'Excavadora IoT Pro ESP32', 'Maquinaria Pesada IoT', 'Excavadora articulada con ESP32 DevKit V1, 74HC595, brazo articulado, luces y telemetría WSS.', '1,2,3,4,5,6,7,8,9', 4850.00, 'bi-truck-front'),
            ('MOD-BAT-02', 'Explorador Táctico Batman IoT', 'Vehículo Explorador', 'Vehículo rápido de tracción diferencial con luces tácticas y control seguro en tiempo real.', '1,2,3,4,7,9', 3600.00, 'bi-car-front-fill')
            """
        )

        # 6. Seed Usuarios Demo (Admin, Usuario Comprador, Invitado)
        cur.execute("SELECT id_rol, codigo FROM roles")
        rol_map = {r["codigo"]: r["id_rol"] for r in cur.fetchall()}

        demo_users = [
            ("ADMIN", "Alan Santiago Rodríguez (Admin)", "admin@empresa-iot.com", "Admin123!", "555-0100"),
            ("USUARIO", "Carlos Comprador Demo", "cliente1@gmail.com", "Cliente123!", "555-0201"),
            ("INVITADO", "Visitante Exhibición", "invitado@demo.com", "Invitado123!", "555-0300"),
        ]
        for rol_cod, nombre, correo, pwd, tel in demo_users:
            cur.execute("SELECT id_usuario FROM usuarios WHERE correo = %s", (correo,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO usuarios (id_rol, nombre_completo, correo, password_hash, telefono, activo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                    """,
                    (rol_map[rol_cod], nombre, correo, hash_password(pwd), tel),
                )

        # 7. Enlazar unidad #1 existente como EXHIBICION (sin perder historial)
        cur.execute("SELECT id_modelo FROM modelos_comerciales WHERE codigo_modelo = 'MOD-EXC-01'")
        mod1 = cur.fetchone()["id_modelo"]
        cur.execute(
            """
            UPDATE vehiculos
            SET numero_serie = COALESCE(numero_serie, 'EXC-ESP32-0001'),
                id_modelo = COALESCE(id_modelo, %s),
                estado_comercial = 'EXHIBICION'
            WHERE id_vehiculo = 1
            """,
            (mod1,),
        )

        # 8. Crear unidad #2 vendida a cliente1@gmail.com para pruebas inmediatas de Mis Vehículos y aislamiento
        cur.execute("SELECT id_usuario FROM usuarios WHERE correo = 'cliente1@gmail.com'")
        cliente1_id = cur.fetchone()["id_usuario"]
        cur.execute("SELECT id_vehiculo FROM vehiculos WHERE numero_serie = 'EXC-ESP32-0002'")
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO vehiculos (nombre, modelo, descripcion, microcontrolador, activo, numero_serie, id_modelo, id_propietario, estado_comercial)
                VALUES ('Excavadora Cliente #1', 'ESP32 DevKit V1', 'Unidad vendida y asignada al comprador demo', 'ESP32', 1, 'EXC-ESP32-0002', %s, %s, 'VENDIDO')
                """,
                (mod1, cliente1_id),
            )
            v2_id = cur.lastrowid
            # Copiar los 9 comandos estándar a la unidad #2
            comandos_base = [
                ("AVANZAR", 1, "1: Avanzar - Q0"),
                ("RETROCEDER", 2, "2: Retroceder - Q7"),
                ("GIRAR_IZQUIERDA", 3, "3: Girar Izquierda - Q2"),
                ("GIRAR_DERECHA", 4, "4: Girar Derecha - Q1"),
                ("SUBIR_BRAZO", 5, "5: Subir Brazo - Q6"),
                ("BAJAR_BRAZO", 6, "6: Bajar Brazo - Q3"),
                ("LUZ", 7, "7: Luz - Q5"),
                ("GRABAR_SECUENCIA", 8, "8: Grabar secuencia"),
                ("DETENER", 9, "9: Detener / Apagar todo"),
            ]
            for nom, cod, desc in comandos_base:
                cur.execute(
                    "INSERT INTO comandos (id_vehiculo, nombre, codigo, descripcion, activo) VALUES (%s, %s, %s, %s, 1)",
                    (v2_id, nom, cod, desc),
                )
            cur.execute("SELECT id_comando FROM comandos WHERE id_vehiculo = %s AND codigo = 9", (v2_id,))
            cmd_detener = cur.fetchone()["id_comando"]
            cur.execute(
                "INSERT INTO estado_vehiculo (id_vehiculo, id_comando, conectado) VALUES (%s, %s, 1)",
                (v2_id, cmd_detener),
            )

        # 9. Registrar evento de migración en auditoría
        cur.execute(
            """
            INSERT INTO auditoria (actor_correo, actor_rol, accion, recurso, resultado, detalle)
            VALUES ('sistema@migracion', 'SYSTEM', 'MIGRACION_BD', 'vehiculo_iot:V4.3.0', 'EXITO', 'Migración incremental 4.3 aplicada conservando historial 4.1/4.2')
            """
        )

        conn.commit()

        # 10. Verificación final de integridad
        cur.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in cur.fetchall()]
        counts = {}
        for t in tables:
            cur.execute(f"SELECT COUNT(*) AS c FROM `{t}`")
            counts[t] = cur.fetchone()["c"]
        print("MIGRACION_V4_3_0_OK")
        print("TABLAS_FINALES:", tables)
        print("CONTEOS_FINALES:", counts)

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
