# API Vehículo IoT

API FastAPI modular que consume los 21 procedimientos almacenados de la práctica y envía movimientos en tiempo real mediante WebSocket.

## Preparación (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Edita `.env` con el endpoint, usuario, contraseña y nombre de tu base MySQL/RDS. El archivo está ignorado por Git. No uses las credenciales de ejemplo en producción y confirma que el Security Group de RDS permita el puerto 3306 únicamente desde tu IP.

## Ejecutar

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Abre `http://localhost:8000/docs`. `GET /` comprueba la API; `GET /health` comprueba también la conexión a MySQL. Si falta `.env`, la documentación y el endpoint raíz funcionan, mientras las operaciones de datos responden 503.

## Pruebas

```powershell
python -m pytest -q
```

Las pruebas no modifican RDS: reemplazan el repositorio por respuestas controladas.

## Pruebas manuales rápidas

1. `GET /health` debe devolver HTTP 200 y `base_de_datos: ok`.
2. `GET /vehiculos` debe listar registros.
3. `POST /vehiculos/1/movimiento` con JSON `{"id_comando": 1, "origen": "THUNDER"}` debe actualizar estado, registrar historial y emitir el evento WebSocket.
4. Conecta Thunder Client a `ws://localhost:8000/ws/vehiculo/1` antes del paso anterior para observar el evento.

## Cliente WebSocket local

Mantén la API ejecutándose y abre una segunda terminal de VS Code:

```powershell
.\.venv\Scripts\Activate.ps1
python cliente_ws.py
```

El cliente se conecta al vehículo `1`, muestra el estado inicial y queda escuchando movimientos individuales y eventos de demos. Usa `Ctrl+C` para cerrarlo.

La base debe contener exactamente los procedimientos con nombres y parámetros definidos en `app/repositories/sp_repository.py`. La guía proporcionada no contiene el SQL que los crea; deben provenir de la práctica 2.4.
