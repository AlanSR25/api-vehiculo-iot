# GUÍA MAESTRA DE CONFIGURACIÓN, ACCESO Y ARQUITECTURA
## Examen Práctico 2.6 - API Vehículo IoT (Amazon EC2 + Amazon RDS + FastAPI + WSS)

> **Documento de referencia técnica para el examen y soporte.**
> Contiene todas las credenciales, llaves SSH, ubicación de archivos, comandos de administración y explicación técnica de la solución.

---

## 1. Datos Generales de la Infraestructura en AWS

* **Tipo de Instancia**: AWS EC2 `t3.small` (Windows Server 2019 Datacenter).
* **IP Elástica (Fija / Permanente)**: `44.194.225.196`
* **Base de Datos**: Amazon RDS MySQL (`vehiculo_iot`) en `instancia-rds-iot.cauwqyrhb42j.us-east-1.rds.amazonaws.com:3306`.
* **Usuario de Windows EC2**: `Administrator`
* **Contraseña de Administrador (RDP de respaldo)**: `U6EkSIKP7SMiO85Q()p!4p7lhVoL-28L`
* **Puertos de Red Abiertos (Security Group y Firewall de Windows)**:
  * `22` (SSH - Administración remota).
  * `8000` (HTTPS / WSS - API FastAPI y WebSocket).
  * `3389` (RDP - Escritorio remoto de Windows).

---

## 2. Enlaces Públicos Oficiales para el Examen

| Servicio | URL Pública | Protocolo |
| :--- | :--- | :---: |
| **Documentación Swagger UI** | `https://44.194.225.196:8000/docs` | HTTPS |
| **Diagnóstico API + RDS** | `https://44.194.225.196:8000/health` | HTTPS |
| **Canal WebSocket Seguro** | `wss://44.194.225.196:8000/ws/vehiculo/1` | WSS |

*(Nota: En el navegador o Thunder Client, ignorar la advertencia de certificado autofirmado "Avanzado > Continuar" o desmarcar "SSL: Verify Host").*

---

## 3. Cómo Conectarse por SSH (Llaves y Acceso Remoto)

### ¿Dónde están guardadas las llaves?
En tu computadora local, dentro de la carpeta del proyecto:
* **Clave privada**: `.ssh_deploy/id_ec2` (protegida, ignorada por `.gitignore`).
* **Clave pública**: `.ssh_deploy/id_ec2.pub`
* **En el servidor EC2**: Registrada en `C:\ProgramData\ssh\administrators_authorized_keys`.

### Comando para conectarte por SSH desde tu computadora:
Abre PowerShell o CMD en la carpeta de este proyecto y ejecuta:

```powershell
ssh -i .ssh_deploy/id_ec2 Administrator@44.194.225.196
```

*(No te pedirá contraseña; entrarás directamente como Administrador).*

### Comando para ejecutar una orden remota sin entrar:
```powershell
ssh -i .ssh_deploy/id_ec2 Administrator@44.194.225.196 "powershell -Command <tu-comando>"
```

---

## 4. Dónde están los Archivos en el Servidor EC2

En el servidor remoto, todo está en la ruta raíz del disco C:
`C:\api_vehiculo_iot_ec2\`

Estructura en la máquina EC2:
```text
C:\api_vehiculo_iot_ec2\
├── .venv\                           # Entorno virtual con Python 3.12 y dependencias
│   └── Scripts\python.exe           # Intérprete que ejecuta Uvicorn
├── .env                             # Credenciales de conexión hacia Amazon RDS
├── app\                             # Código fuente de FastAPI
│   ├── core\
│   │   ├── config.py                # Carga de variables de entorno
│   │   └── database.py              # Pool de conexiones MySQL y método ping()
│   ├── models\schemas.py            # Modelos Pydantic (validación de datos)
│   ├── repositories\sp_repository.py# Consumo de los 21 Stored Procedures
│   ├── routers\                     # Endpoints REST (vehículos, comandos, demos, estado)
│   ├── services\demo_runner.py      # Gestor asíncrono en segundo plano para secuencias DEMO
│   ├── websocket\connection_manager.py # Difusión (broadcast) de eventos WSS
│   └── main.py                      # App principal FastAPI y ruta /ws/vehiculo/{id}
├── certificados\                    # Certificados TLS para HTTPS y WSS
│   ├── server-cert.pem              # Certificado x509 válido para la IP 44.194.225.196
│   └── server-key.pem               # Clave privada RSA
├── generar_certificado.py           # Script generador del certificado
└── pruebas_examen.http              # Peticiones listas para ejecutar en VS Code
```

---

## 5. Cómo está Configurada la Persistencia (Segundo Plano)

La API **no se ejecuta desde una consola interactiva** (así evitamos que se caiga al cerrar VS Code o RDP).

* Está configurada como una **Tarea Programada de Windows** llamada:
  `FastAPI_IoT`
* **Cuenta con la que corre**: `NT AUTHORITY\SYSTEM` (máximos privilegios, independiente de usuarios).
* **Disparador**: `AtStartup` (**arranca sola automáticamente** cada vez que la máquina EC2 se enciende o reinicia).
* **Comando que ejecuta la tarea**:
  ```text
  C:\api_vehiculo_iot_ec2\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile C:\api_vehiculo_iot_ec2\certificados\server-key.pem --ssl-certfile C:\api_vehiculo_iot_ec2\certificados\server-cert.pem
  ```

### Comandos de control del servicio (vía SSH o PowerShell en EC2):
* **Ver si está corriendo**:
  ```powershell
  (Get-ScheduledTask -TaskName 'FastAPI_IoT').State
  ```
* **Reiniciar el servicio**:
  ```powershell
  Stop-ScheduledTask -TaskName 'FastAPI_IoT'; Start-ScheduledTask -TaskName 'FastAPI_IoT'
  ```
* **Comprobar si el puerto 8000 está escuchando**:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000
  ```

---

## 6. Qué Hace y Qué NO Hace la Solución (Reglas de Negocio)

### ✅ Lo que SÍ hace:
1. **21 Stored Procedures**: Todos los accesos a datos pasan obligatoriamente por los 21 procedimientos almacenados creados en MySQL (`vehiculo_iot`), sin SQL quemado en código.
2. **Movimiento Individual (`POST /vehiculos/{id}/movimiento`)**:
   * Valida que el vehículo y el comando existan y estén activos (`activo = 1`).
   * En una **sola transacción atómica (`ejecutar_movimiento_individual_tx`)**:
     * Actualiza el estado (`sp_actualizar_estado`).
     * Registra en la bitácora (`sp_registrar_historial`).
   * Difunde inmediatamente el evento `MOVIMIENTO_INDIVIDUAL` a **todos los clientes WebSocket** conectados a ese vehículo.
3. **Consulta de Historial (`GET /vehiculos/{id}/historial`)**:
   * Devuelve como máximo los **10 movimientos más recientes** en orden cronológico inverso (del más nuevo al más viejo).
4. **Secuencias DEMO en Tiempo Real (`POST /vehiculos/{id}/demos/{id}/iniciar`)**:
   * Lee los movimientos de `sp_obtener_movimientos_demo`.
   * Ejecuta en segundo plano (`asyncio.Task`) paso a paso:
     * Emite `DEMO_INICIO` (total movimientos).
     * Por cada movimiento emite `MOVIMIENTO_DEMO` (orden, comando, duracion_ms, pausa_ms).
     * **Actualiza el último estado en RDS** (`sp_actualizar_estado`).
     * Espera con exactitud los milisegundos de `duracion_ms` y `pausa_ms`.
     * Emite `DEMO_FINALIZADA`.
5. **Control de Concurrencia y Cancelación**:
   * Si una demo ya está corriendo en el vehículo, rechaza otra con `HTTP 409 Conflict`.
   * Con `POST /vehiculos/{id}/demos/cancelar`, detiene los pasos posteriores y emite `DEMO_CANCELADA` por WSS.
6. **Canal WSS**:
   * Al conectar un cliente, le entrega inmediatamente el estado guardado en RDS (`CONEXION_ESTABLECIDA`).
   * Soporta múltiples conexiones en paralelo por vehículo.

### ❌ Lo que NO hace (Regla Crítica del Examen):
* **La DEMO NO agrega registros a la tabla `historial`**:
  Solo actualiza el estado actual (`sp_actualizar_estado`). El historial queda reservado **únicamente** para movimientos manuales individuales (`POST /movimiento`).

---

## 7. Mapeo Rápido de los 21 Stored Procedures

| # | Grupo | Procedimiento Almacenado | Endpoint FastAPI |
|---|---|---|---|
| 1 | Vehículos | `sp_crear_vehiculo` | `POST /vehiculos` |
| 2 | Vehículos | `sp_obtener_vehiculos` | `GET /vehiculos` |
| 3 | Vehículos | `sp_obtener_vehiculo` | `GET /vehiculos/{id_vehiculo}` |
| 4 | Vehículos | `sp_actualizar_vehiculo` | `PUT /vehiculos/{id_vehiculo}` |
| 5 | Vehículos | `sp_eliminar_vehiculo` | `DELETE /vehiculos/{id_vehiculo}` |
| 6 | Comandos | `sp_crear_comando` | `POST /comandos` |
| 7 | Comandos | `sp_obtener_comandos_vehiculo` | `GET /comandos/vehiculo/{id_vehiculo}` |
| 8 | Comandos | `sp_actualizar_comando` | `PUT /comandos/{id_comando}` |
| 9 | Comandos | `sp_eliminar_comando` | `DELETE /comandos/{id_comando}` |
| 10 | Estado | `sp_actualizar_estado` | `PUT /vehiculos/{id_vehiculo}/estado` |
| 11 | Estado | `sp_obtener_estado` | `GET /vehiculos/{id_vehiculo}/estado` |
| 12 | Historial | `sp_registrar_historial` | Interno en `POST /vehiculos/{id}/movimiento` |
| 13 | Historial | `sp_obtener_historial` | `GET /vehiculos/{id_vehiculo}/historial` |
| 14 | DEMOs | `sp_crear_demo` | `POST /demos` |
| 15 | DEMOs | `sp_obtener_demos` | `GET /vehiculos/{id_vehiculo}/demos` |
| 16 | DEMOs | `sp_actualizar_demo` | `PUT /demos/{id_demo}` |
| 17 | DEMOs | `sp_eliminar_demo` | `DELETE /demos/{id_demo}` |
| 18 | Movs DEMO | `sp_agregar_movimiento_demo` | `POST /demos/{id_demo}/movimientos` |
| 19 | Movs DEMO | `sp_obtener_movimientos_demo`| `GET /demos/{id_demo}/movimientos` |
| 20 | Movs DEMO | `sp_actualizar_movimiento_demo` | `PUT /demos/movimientos/{id_movimiento}` |
| 21 | Movs DEMO | `sp_eliminar_movimiento_demo` | `DELETE /demos/movimientos/{id_movimiento}` |

---

## 8. Preguntas Clave para Responder al Profesor

1. **¿Por qué la base de datos no está abierta a todo Internet?**
   * *Respuesta*: El Security Group de Amazon RDS solo acepta conexiones entrantes en el puerto 3306 desde la IP privada de la instancia EC2 (`172.31.6.104`) y la IP administrativa del alumno.
2. **¿Por qué la API sigue viva si cierras la computadora?**
   * *Respuesta*: Porque está corriendo en una máquina virtual de AWS EC2 bajo el servicio de sistema `SYSTEM` en segundo plano con inicio automático `AtStartup`.
3. **¿Cómo garantizas que el movimiento individual no quede a medias si falla la base?**
   * *Respuesta*: Se implementó una transacción atómica (`ejecutar_movimiento_individual_tx`), que ejecuta `sp_actualizar_estado` y `sp_registrar_historial`; si alguna falla, se ejecuta `rollback()`.
4. **¿Cuál es la diferencia entre un POST de movimiento y una DEMO?**
   * *Respuesta*: El POST individual representa una acción de teleoperación manual directa (actualiza estado + genera historial). La DEMO es una rutina preprogramada automatizada de N pasos en tiempo real (actualiza el estado en vivo pero no satura la bitácora de historial).
