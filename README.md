# API Vehículo IoT - Examen Práctico Tema 2

API REST y WebSocket segura (HTTPS/WSS) desarrollada en Python con FastAPI y Programación Orientada a Objetos, desplegada en **Amazon EC2** y conectada a una base de datos MySQL en **Amazon RDS** (`vehiculo_iot`), consumiendo los **21 procedimientos almacenados** de la arquitectura IoT.

---

## Enlaces Públicos

* **Documentación Swagger UI (HTTPS)**: `https://44.194.225.196:8000/docs`
* **Diagnóstico de Salud (HTTPS)**: `https://44.194.225.196:8000/health`
* **Canal WebSocket Seguro (WSS)**: `wss://44.194.225.196:8000/ws/vehiculo/{id_vehiculo}`

---

## Arquitectura y Tecnologías

```
[Cliente Remoto / Thunder Client / ESP8266]
                 │  ▲
      HTTPS/WSS  │  │  Puerto 8000 (TLS Autofirmado)
                 ▼  │
      [Amazon EC2 (Windows Server 2019)]
           FastAPI + Uvicorn (Daemon persistente)
                 │  ▲
       MySQL TCP │  │  Puerto 3306
                 ▼  │
      [Amazon RDS for MySQL (vehiculo_iot)]
           6 Tablas + 21 Stored Procedures
```

---

## Mapeo de los 21 Procedimientos Almacenados

| # | Grupo | Procedimiento Almacenado | Método HTTP | Endpoint API | Descripción |
|---|---|---|---|---|---|
| 1 | **Vehículos** | `sp_crear_vehiculo` | `POST` | `/vehiculos` | Registra un nuevo vehículo |
| 2 | **Vehículos** | `sp_obtener_vehiculos` | `GET` | `/vehiculos` | Lista todos los vehículos |
| 3 | **Vehículos** | `sp_obtener_vehiculo` | `GET` | `/vehiculos/{id_vehiculo}` | Obtiene información de un vehículo |
| 4 | **Vehículos** | `sp_actualizar_vehiculo` | `PUT` | `/vehiculos/{id_vehiculo}` | Actualiza datos del vehículo |
| 5 | **Vehículos** | `sp_eliminar_vehiculo` | `DELETE` | `/vehiculos/{id_vehiculo}` | Elimina el vehículo y registros asociados |
| 6 | **Comandos** | `sp_crear_comando` | `POST` | `/comandos` | Registra un comando para un vehículo |
| 7 | **Comandos** | `sp_obtener_comandos_vehiculo` | `GET` | `/comandos/vehiculo/{id_vehiculo}` | Lista comandos por vehículo ordenados |
| 8 | **Comandos** | `sp_actualizar_comando` | `PUT` | `/comandos/{id_comando}` | Modifica un comando existente |
| 9 | **Comandos** | `sp_eliminar_comando` | `DELETE` | `/comandos/{id_comando}` | Elimina un comando |
| 10 | **Estado** | `sp_actualizar_estado` | `PUT` | `/vehiculos/{id_vehiculo}/estado` | Actualiza comando actual y conexión |
| 11 | **Estado** | `sp_obtener_estado` | `GET` | `/vehiculos/{id_vehiculo}/estado` | Consulta el último estado del vehículo |
| 12 | **Historial** | `sp_registrar_historial` | `POST` | Interno en `/vehiculos/{id}/movimiento` | Registra movimiento individual en historial |
| 13 | **Historial** | `sp_obtener_historial` | `GET` | `/vehiculos/{id_vehiculo}/historial` | Obtiene máx. 10 movimientos recientes |
| 14 | **DEMOs** | `sp_crear_demo` | `POST` | `/demos` | Crea una secuencia de demostración |
| 15 | **DEMOs** | `sp_obtener_demos` | `GET` | `/vehiculos/{id_vehiculo}/demos` | Consulta DEMOs de un vehículo |
| 16 | **DEMOs** | `sp_actualizar_demo` | `PUT` | `/demos/{id_demo}` | Modifica una DEMO |
| 17 | **DEMOs** | `sp_eliminar_demo` | `DELETE` | `/demos/{id_demo}` | Elimina una DEMO |
| 18 | **Movs. DEMO** | `sp_agregar_movimiento_demo` | `POST` | `/demos/{id_demo}/movimientos` | Agrega paso con duración y pausa en ms |
| 19 | **Movs. DEMO** | `sp_obtener_movimientos_demo`| `GET` | `/demos/{id_demo}/movimientos` | Consulta pasos ordenados por posición |
| 20 | **Movs. DEMO** | `sp_actualizar_movimiento_demo` | `PUT` | `/demos/movimientos/{id_movimiento}` | Actualiza paso de la DEMO |
| 21 | **Movs. DEMO** | `sp_eliminar_movimiento_demo` | `DELETE` | `/demos/movimientos/{id_movimiento}` | Elimina un paso de la DEMO |

### Endpoints Especiales de Control
* `POST /vehiculos/{id_vehiculo}/movimiento`: Ejecuta `sp_actualizar_estado` + `sp_registrar_historial` en una **única transacción atómica** y emite por WSS.
* `POST /vehiculos/{id_vehiculo}/demos/{id_demo}/iniciar`: Ejecuta la DEMO en segundo plano, transmite N pasos por WSS, actualiza el estado pero **NO registra en historial**.
* `POST /vehiculos/{id_vehiculo}/demos/cancelar`: Cancela la DEMO activa de inmediato.

---

## Eventos WebSocket (WSS)

Canal: `wss://44.194.225.196:8000/ws/vehiculo/{id_vehiculo}`

### 1. Conexión Establecida (Estado Inicial)
```json
{
  "evento": "CONEXION_ESTABLECIDA",
  "id_vehiculo": 1,
  "estado": {
    "id_vehiculo": 1,
    "vehiculo": "Excavadora IoT",
    "id_comando": 1,
    "comando": "AVANZAR",
    "codigo": 1,
    "conectado": 1,
    "fecha_actualizacion": "2026-10-21T00:18:44"
  },
  "timestamp": "2026-10-21T00:18:44.326785+00:00"
}
```

### 2. Movimiento Individual (Vía POST)
```json
{
  "evento": "MOVIMIENTO_INDIVIDUAL",
  "id_vehiculo": 1,
  "comando": "AVANZAR",
  "codigo": 1,
  "origen": "THUNDER-CLIENT",
  "timestamp": "2026-10-21T00:20:10.123456+00:00"
}
```

### 3. Secuencia DEMO en Tiempo Real
* **Inicio**:
  ```json
  {"evento": "DEMO_INICIO", "id_vehiculo": 1, "id_demo": 1, "total_movimientos": 8, "timestamp": "..."}
  ```
* **Cada paso temporizado**:
  ```json
  {
    "evento": "MOVIMIENTO_DEMO",
    "id_vehiculo": 1,
    "orden": 1,
    "comando": "AVANZAR",
    "codigo": 1,
    "duracion_ms": 2000,
    "pausa_ms": 400,
    "timestamp": "..."
  }
  ```
* **Finalización**:
  ```json
  {"evento": "DEMO_FINALIZADA", "id_vehiculo": 1, "id_demo": 1, "timestamp": "..."}
  ```
