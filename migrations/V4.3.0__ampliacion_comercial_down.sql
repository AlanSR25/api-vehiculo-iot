-- ============================================================================
-- MIGRACIÓN SQL VERSIONADA: V4.3.0 (DOWN / REVERSIÓN)
-- Reversión segura para entornos de prueba sin borrar datos históricos de 4.1/4.2
-- ============================================================================

USE vehiculo_iot;

-- 1. Eliminar tablas nuevas en orden inverso de dependencias
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS sesiones_invitado;

-- 2. Retirar FKs y columnas agregadas a `demos`
ALTER TABLE demos DROP FOREIGN KEY fk_demos_usuario;
ALTER TABLE demos DROP COLUMN tipo_demo;
ALTER TABLE demos DROP COLUMN id_usuario;

-- 3. Retirar FKs y columnas agregadas a `vehiculos`
ALTER TABLE vehiculos DROP FOREIGN KEY fk_vehiculos_propietario;
ALTER TABLE vehiculos DROP FOREIGN KEY fk_vehiculos_modelo;
ALTER TABLE vehiculos DROP COLUMN soporte_autorizado;
ALTER TABLE vehiculos DROP COLUMN estado_comercial;
ALTER TABLE vehiculos DROP COLUMN id_propietario;
ALTER TABLE vehiculos DROP COLUMN id_modelo;
ALTER TABLE vehiculos DROP COLUMN numero_serie;

-- 4. Eliminar tablas catálogo
DROP TABLE IF EXISTS modelos_comerciales;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS roles;
