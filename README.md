# Aplicación Web de Control y Monitoreo IoT en Tiempo Real
**Práctica 4.1 (Control) & Práctica 4.2 (Monitoreo)**
**Alumno:** Alan Santiago Rodríguez  
**Matrícula:** 22200767  
**Año:** 2026  
**Repositorio GitHub:** [https://github.com/AlanSR25/api-vehiculo-iot](https://github.com/AlanSR25/api-vehiculo-iot)  
**Despliegue GitHub Pages:** [https://alansr25.github.io/api-vehiculo-iot/](https://alansr25.github.io/api-vehiculo-iot/)  

---

## 1. Enlaces Públicos y Contratos del Sistema

* **Frontend Web (GitHub Pages)**: `https://alansr25.github.io/api-vehiculo-iot/`
* **Base API HTTPS (Cloudflare Tunnel)**: `https://bath-sunrise-stomach-grown.trycloudflare.com`
* **Documentación Swagger / OpenAPI**: `https://bath-sunrise-stomach-grown.trycloudflare.com/docs`
* **Canal WebSocket Seguro (WSS)**: `wss://bath-sunrise-stomach-grown.trycloudflare.com/ws/vehiculo/1`
* **Diagnóstico de Salud (Health)**: `https://bath-sunrise-stomach-grown.trycloudflare.com/health`
* **GET Último Estado**: `GET /vehiculos/1/estado`
* **GET Historial (10 individuales)**: `GET /vehiculos/1/historial`
* **IP Directa EC2 (Backup)**: `44.194.225.196:8000`

---

## 2. Diagrama de Arquitectura Integral

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CLIENTES (Mobile First / Desktop)                     │
│  - GitHub Pages: https://alansr25.github.io/api-vehiculo-iot/          │
│  - Vista 1: CONTROL (Joystick táctil PointerEvents, DETENER, DEMO)     │
│  - Vista 2: MONITOREO (Tarjeta último estado + Tabla 10 movimientos)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS (Fetch REST) / WSS (WebSocket)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              CLOUDFLARE EDGE & TUNNEL (Certificado TLS Válido)         │
│  - Endpoint: bath-sunrise-stomach-grown.trycloudflare.com              │
│  - Sin advertencias SSL en navegadores móviles (iOS / Android)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ localhost:8000
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  AMAZON EC2 (Windows Server 2019)                      │
│  - FastAPI + Uvicorn (Daemon persistente bajo Administrador/SYSTEM)    │
│  - 21 Servicios REST mapeados a Stored Procedures                      │
│  - WebSocket Hub bidireccional multicliente (/ws/vehiculo/{id})        │
│  - CORS Middleware: orígenes abiertos (*) para GitHub Pages            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ MySQL TCP (Puerto 3306)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  AMAZON RDS for MySQL (vehiculo_iot)                   │
│  - 6 Tablas relacionales (vehiculos, comandos, estado, historial, etc.) │
│  - 21 Procedimientos almacenados para aislamiento y seguridad SQL      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Estructura de Carpetas del Proyecto

```
api_vehiculo_iot_ec2/
├── assets/
│   ├── css/
│   │   └── styles.css               # Estilos oscuros Mobile-First, tabs y tablas
│   ├── icons/
│   │   └── favicon.svg              # Favicon SVG vectorial integrado
│   └── js/
│       ├── components/
│       │   ├── joystick.js          # Joystick táctil circular virtual con PointerEvents
│       │   └── monitoreo.js         # Mánager reactivo de tarjeta y tabla de monitoreo
│       ├── services/
│       │   ├── apiService.js        # Cliente Fetch HTTP con timeout y AbortController
│       │   └── wsService.js         # Cliente WebSocket con reconexión automática
│       ├── state/
│       │   └── appState.js          # Estado central reactivo de la UI
│       ├── config.js                # URLs y constantes de la aplicación
│       └── main.js                  # Orquestador principal de control y monitoreo
├── frontend/                        # Copia sincronizada para despliegues alternativos
│   ├── assets/...
│   └── index.html
├── index.html                       # Documento principal HTML5 semántico
└── README.md                        # Memoria técnica y documentación
```

---

## 4. Reglas de Negocio Implementadas

1. **Prioridad Absoluta de DETENER (Código 9)**:
   * El botón de parada de emergencia envía inmediatamente el comando `9` al backend y aborta cualquier DEMO en ejecución.
2. **Separación Estricta de Historial vs. DEMO**:
   * Los movimientos generados por joystick o botones táctiles se persisten en `vehiculo_iot.historial` vía REST y se transmiten por WSS como `MOVIMIENTO_INDIVIDUAL`.
   * Los pasos internos de secuencias DEMO (`MOVIMIENTO_DEMO`) actualizan en tiempo real la **tarjeta de último estado**, pero **NO se agregan a la tabla de historial individual** para preservar la integridad de auditoría solicitada por el contrato de negocio.
3. **Sincronización Antirraces (Debounce)**:
   * Al recibir eventos WSS de movimientos individuales, el componente de monitoreo espera 450 ms para permitir que la transacción en Amazon RDS MySQL termine su commit antes de refrescar el historial mediante `GET /vehiculos/1/historial`.
4. **Tres Indicadores de Salud Independientes**:
   * **WebSocket WSS**: En línea / Conectando / Desconectado (basado en el ciclo de vida del socket).
   * **API AWS (EC2)**: Disponible / No disponible (evaluado con endpoint `/health`).
   * **Amazon RDS**: Disponible / No disponible (evaluado con `base_de_datos: ok` dentro de `/health`).

---

## 5. Casos de Prueba y Verificación

| # | Caso de Prueba | Procedimiento | Resultado Esperado |
|---|---|---|---|
| 1 | **Carga Inicial de Monitoreo** | Clic en la pestaña "Monitoreo" | Se consulta `GET /vehiculos/1/estado` y `GET /vehiculos/1/historial`. La tarjeta muestra el comando actual y la tabla muestra hasta 10 filas con numeración, comando, fecha y hora. |
| 2 | **Comando desde Pestaña Control** | Mover Joystick a AVANZAR en la pestaña "Control" | Se envía POST `comando: 1`. El badge WSS confirma el evento. Al pasar a "Monitoreo", la tarjeta y la primera fila reflejan AVANZAR. |
| 3 | **Evento Externo Multicliente** | Enviar comando desde Thunder Client / Swagger | Monitoreo reacciona de inmediato vía WSS sin recargar la página. La tarjeta se actualiza en vivo y la tabla resincroniza sus 10 registros. |
| 4 | **Aislamiento de DEMO** | Iniciar DEMO #1 desde Control | La tarjeta de monitoreo muestra `MOVIMIENTO_DEMO` y el número de paso en tiempo real. La tabla de 10 movimientos **mantiene intactos** los comandos individuales previos. |
| 5 | **Reconexión Resiliente** | Cerrar y volver a abrir la red | El badge de WebSocket pasa a "Conectando..." y luego "En línea". Al reconectar, se ejecuta `cargarDatosCompletos()` para recuperar posibles eventos perdidos. |

---

## 6. Créditos Obligatorios

* **Alumno:** Alan Santiago Rodríguez
* **Matrícula:** 22200767
* **Materia:** Programación e Integración de Sistemas IoT
* **Año:** 2026
