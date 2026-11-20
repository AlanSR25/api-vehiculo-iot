-- ============================================================================
-- MIGRACIÓN SQL VERSIONADA: V4.3.0 (UP)
-- Proyecto: Plataforma Comercial Multiusuario IoT (Control + Monitoreo + Admin)
-- Base de datos: vehiculo_iot (Amazon RDS MySQL 8)
-- Autor: Alan Santiago Rodríguez (Matrícula: 22200767)
-- Nota MySQL: Las sentencias DDL (CREATE/ALTER) realizan commit implícito.
-- Asegúrese de contar con el respaldo backups/respaldo_4_2_previo_4_3.sql.
-- ============================================================================

USE vehiculo_iot;

-- 1. Catálogo de Roles (RBAC)
CREATE TABLE IF NOT EXISTS roles (
    id_rol INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(60) NOT NULL,
    descripcion VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Tabla de Usuarios / Clientes
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Catálogo de Modelos Comerciales (distinto de Unidad Física)
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Sesiones Temporales de Invitado (Reserva exclusiva por unidad de exhibición)
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Bitácora de Auditoría (sin secretos ni contraseñas)
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Ampliación incremental de `vehiculos` (conserva PK, datos e historial previos)
-- Nota: El script aplicador verifica existencia de columnas antes de ALTER para idempotencia.
-- ALTER TABLE vehiculos ADD COLUMN numero_serie VARCHAR(60) NULL UNIQUE;
-- ALTER TABLE vehiculos ADD COLUMN id_modelo INT NULL;
-- ALTER TABLE vehiculos ADD COLUMN id_propietario INT NULL;
-- ALTER TABLE vehiculos ADD COLUMN estado_comercial ENUM('DISPONIBLE','VENDIDO','EXHIBICION','MANTENIMIENTO','INACTIVO') NOT NULL DEFAULT 'EXHIBICION';
-- ALTER TABLE vehiculos ADD COLUMN soporte_autorizado TINYINT(1) NOT NULL DEFAULT 0;
-- ALTER TABLE vehiculos ADD CONSTRAINT fk_vehiculos_modelo FOREIGN KEY (id_modelo) REFERENCES modelos_comerciales(id_modelo) ON DELETE SET NULL;
-- ALTER TABLE vehiculos ADD CONSTRAINT fk_vehiculos_propietario FOREIGN KEY (id_propietario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL;

-- 7. Ampliación incremental de `demos` (demos de fábrica vs demos privadas)
-- ALTER TABLE demos ADD COLUMN id_usuario INT NULL;
-- ALTER TABLE demos ADD COLUMN tipo_demo ENUM('FABRICA','PRIVADA') NOT NULL DEFAULT 'FABRICA';
-- ALTER TABLE demos ADD CONSTRAINT fk_demos_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL;

-- 8. Semilla de Roles Base
INSERT IGNORE INTO roles (codigo, nombre, descripcion) VALUES
('ADMIN', 'Administrador', 'Empresa comercializadora: inventario, clientes, asignaciones, demos de fábrica y auditoría'),
('USUARIO', 'Usuario Comprador', 'Cliente propietario: controla y monitorea únicamente sus unidades y gestiona sus demos privadas'),
('INVITADO', 'Invitado / Prospecto', 'Cliente potencial: explora catálogo público y solicita sesión temporal limitada de exhibición');

-- 9. Semilla de Modelos Comerciales
INSERT IGNORE INTO modelos_comerciales (codigo_modelo, nombre, categoria, descripcion, comandos_soportados, precio_referencia, imagen_icono) VALUES
('MOD-EXC-01', 'Excavadora IoT Pro ESP32', 'Maquinaria Pesada IoT', 'Excavadora articulada con ESP32 DevKit V1, registro 74HC595, control de brazo, luces y telemetría WSS.', '1,2,3,4,5,6,7,8,9', 4850.00, 'bi-truck-front'),
('MOD-BAT-02', 'Explorador Táctico Batman IoT', 'Vehículo Explorador', 'Vehículo rápido de tracción diferencial con luces tácticas y control seguro en tiempo real.', '1,2,3,4,7,9', 3600.00, 'bi-car-front-fill');
