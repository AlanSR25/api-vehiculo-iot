-- =====================================================
-- EXAMEN TEMA 2: CONFIGURACIÓN EXACTA PARA ESP32 + 74HC595
-- Base de datos: vehiculo_iot (Amazon RDS)
-- =====================================================

USE vehiculo_iot;

-- 1. Desactivar temporalmente restricciones de claves foráneas
SET SESSION FOREIGN_KEY_CHECKS = 0;

-- 2. Limpiar registros anteriores conservando procedimientos y tablas
DELETE FROM demo_movimientos;
DELETE FROM estado_vehiculo;
DELETE FROM historial_comandos;
DELETE FROM demos;
DELETE FROM comandos;
DELETE FROM vehiculos;

-- 3. Reiniciar contadores AUTO_INCREMENT
ALTER TABLE demo_movimientos AUTO_INCREMENT = 1;
ALTER TABLE estado_vehiculo AUTO_INCREMENT = 1;
ALTER TABLE historial_comandos AUTO_INCREMENT = 1;
ALTER TABLE demos AUTO_INCREMENT = 1;
ALTER TABLE comandos AUTO_INCREMENT = 1;
ALTER TABLE vehiculos AUTO_INCREMENT = 1;

-- 4. Registrar el vehículo físico: ESP32 DevKit V1
INSERT INTO vehiculos
    (id_vehiculo, nombre, modelo, descripcion, microcontrolador, activo)
VALUES
    (1, 'Excavadora IoT',
     'ESP32 DevKit V1',
     'Excavadora controlada por ESP32 y registro de desplazamiento 74HC595 vía WebSocket (WSS)',
     'ESP32', 1);

-- 5. Registrar los comandos sincronizados con el código Arduino/ESP32:
--    W -> Avanzar (Q0)
--    S -> Retroceder (Q7)
--    A -> Izquierda (Q2)
--    D -> Derecha (Q1)
--    1 -> Subir brazo/garra (Q6)
--    2 -> Bajar brazo/garra (Q3)
--    3 -> Luces (Q5)
--    Q -> Detener / Apagar todo
INSERT INTO comandos
    (id_comando, id_vehiculo, nombre, codigo, descripcion, activo)
VALUES
    (1, 1, 'AVANZAR',         1, 'W: Avanzar - Activa salida Q0 (0b00000001)', 1),
    (2, 1, 'RETROCEDER',      2, 'S: Retroceder - Activa salida Q7 (0b10000000)', 1),
    (3, 1, 'GIRAR_IZQUIERDA', 3, 'A: Izquierda - Activa salida Q2 (0b00000100)', 1),
    (4, 1, 'GIRAR_DERECHA',   4, 'D: Derecha - Activa salida Q1 (0b00000010)', 1),
    (5, 1, 'SUBIR_BRAZO',     5, '1: Subir brazo/garra - Activa salida Q6 (0b01000000)', 1),
    (6, 1, 'BAJAR_BRAZO',     6, '2: Bajar brazo/garra - Activa salida Q3 (0b00001000)', 1),
    (7, 1, 'LUCES',           7, '3: Luces - Activa salida Q5 (0b00100000)', 1),
    (8, 1, 'DETENER',         8, 'Q: Apagar / Detener todo - Salidas en 0b00000000', 1);

-- 6. Crear la DEMO de la excavadora
INSERT INTO demos
    (id_demo, id_vehiculo, nombre, descripcion, activo)
VALUES
    (1, 1,
     'Demo Excavadora ESP32',
     'Secuencia automática: Avanzar, Retroceder, Izquierda, Derecha, Subir, Bajar, Luces y Detener',
     1);

-- 7. Registrar los movimientos exactos de la función procesarDemo() de Arduino:
--    Paso 0: Avanzar (2000 ms)
--    Paso 1: Retroceder (2000 ms)
--    Paso 2: Izquierda (2000 ms)
--    Paso 3: Derecha (2000 ms)
--    Paso 4: Subir (2000 ms)
--    Paso 5: Bajar (2000 ms)
--    Paso 6: Luces (2000 ms)
--    Fin: Detener / Apagar todo
INSERT INTO demo_movimientos
    (id_demo_movimiento, id_demo, id_comando, orden, duracion_ms, pausa_ms)
VALUES
    (1, 1, 1, 1, 2000, 0),
    (2, 1, 2, 2, 2000, 0),
    (3, 1, 3, 3, 2000, 0),
    (4, 1, 4, 4, 2000, 0),
    (5, 1, 5, 5, 2000, 0),
    (6, 1, 6, 6, 2000, 0),
    (7, 1, 7, 7, 2000, 0),
    (8, 1, 8, 8, 0,    0);

-- 8. Inicializar el estado del vehículo en reposo
INSERT INTO estado_vehiculo
    (id_vehiculo, id_comando, conectado)
VALUES
    (1, NULL, 0);

-- 9. Reactivar comprobación de claves foráneas
SET SESSION FOREIGN_KEY_CHECKS = 1;

-- 10. Comprobación final
SELECT id_vehiculo, nombre, modelo, microcontrolador FROM vehiculos;
SELECT id_comando, codigo, nombre, descripcion FROM comandos ORDER BY codigo;
SELECT id_demo, nombre FROM demos;
SELECT dm.orden, c.nombre AS comando, dm.duracion_ms, dm.pausa_ms 
FROM demo_movimientos dm 
JOIN comandos c ON dm.id_comando = c.id_comando 
ORDER BY dm.orden;

