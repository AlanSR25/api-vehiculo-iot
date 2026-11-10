import mysql.connector

conn = mysql.connector.connect(
    host='instancia-rds-iot.cauwqyrhb42j.us-east-1.rds.amazonaws.com',
    port=3306,
    user='admin',
    password='Admin1234#',
    database='vehiculo_iot',
    use_pure=True
)
cur = conn.cursor()

cur.execute('SET FOREIGN_KEY_CHECKS = 0')
cur.execute('DELETE FROM demo_movimientos')
cur.execute('DELETE FROM historial_comandos')
cur.execute('DELETE FROM estado_vehiculo')
cur.execute('DELETE FROM demos')
cur.execute('DELETE FROM comandos')
cur.execute('ALTER TABLE comandos AUTO_INCREMENT = 1')
cur.execute('ALTER TABLE demo_movimientos AUTO_INCREMENT = 1')

comandos = [
    (1, 1, 'AVANZAR', 1, '1: Avanzar - Q0', 1),
    (2, 1, 'RETROCEDER', 2, '2: Retroceder - Q7', 1),
    (3, 1, 'GIRAR_IZQUIERDA', 3, '3: Girar Izquierda - Q2', 1),
    (4, 1, 'GIRAR_DERECHA', 4, '4: Girar Derecha - Q1', 1),
    (5, 1, 'SUBIR_BRAZO', 5, '5: Subir Brazo - Q6', 1),
    (6, 1, 'BAJAR_BRAZO', 6, '6: Bajar Brazo - Q3', 1),
    (7, 1, 'LUZ', 7, '7: Luz - Q5', 1),
    (8, 1, 'DEMO', 8, '8: Demo automatica', 1),
    (9, 1, 'DETENER', 9, '9: Detener / Apagar todo', 1)
]

cur.executemany(
    'INSERT INTO comandos (id_comando, id_vehiculo, nombre, codigo, descripcion, activo) VALUES (%s, %s, %s, %s, %s, %s)',
    comandos
)

cur.execute("INSERT INTO demos (id_demo, id_vehiculo, nombre, descripcion, activo) VALUES (1, 1, 'Demo 1 a 9', 'Secuencia numerada 1 a 7 y fin 9', 1)")

demo_movs = [
    (1, 1, 1, 1, 2000, 0),
    (2, 1, 2, 2, 2000, 0),
    (3, 1, 3, 3, 2000, 0),
    (4, 1, 4, 4, 2000, 0),
    (5, 1, 5, 5, 2000, 0),
    (6, 1, 6, 6, 2000, 0),
    (7, 1, 7, 7, 2000, 0),
    (8, 1, 9, 8, 0, 0),
]
cur.executemany(
    'INSERT INTO demo_movimientos (id_demo_movimiento, id_demo, id_comando, orden, duracion_ms, pausa_ms) VALUES (%s, %s, %s, %s, %s, %s)',
    demo_movs
)

cur.execute('INSERT INTO estado_vehiculo (id_vehiculo, id_comando, conectado) VALUES (1, 9, 0)')
cur.execute('SET FOREIGN_KEY_CHECKS = 1')
conn.commit()

print('Comandos actualizados exitosamente en RDS:')
cur.execute('SELECT id_comando, codigo, nombre, descripcion FROM comandos ORDER BY codigo')
for c in cur.fetchall():
    print(c)

conn.close()

