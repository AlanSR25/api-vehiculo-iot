# Evidencias, Matrices y Conclusiones Personales — Práctica 4.3
**Tecnológico Nacional de México campus Pachuca**  
**Ingeniería en Sistemas Computacionales · Implementación de soluciones IoT**  
**Docente:** M.C. Víctor Manuel Pinedo Fernández  
**Alumno:** Alan Santiago Rodríguez (Matrícula: 22200767) · 2026  

---

## 1. Enlaces Oficiales de Entrega (Sección 15)

* **15.1 URL Pública HTTPS del Frontend Integrado (Control + Monitoreo + Administración)**:  
  `https://alansr25.github.io/api-vehiculo-iot/`
* **15.2 URL del Repositorio Original Actualizado**:  
  `https://github.com/AlanSR25/api-vehiculo-iot`
* **15.2 URL de Documentación Swagger / OpenAPI (`/docs`)**:  
  `https://platinum-nissan-orlando-proved.trycloudflare.com/docs`
* **15.2 Diagnóstico de Salud (`/health`)**:  
  `https://platinum-nissan-orlando-proved.trycloudflare.com/health`
* **15.2 Suite Automatizada de Pruebas (P01–P17)**:  
  [`tests/test_seguridad_4_3.py`](tests/test_seguridad_4_3.py)

---

## 2. Inventario de Base de Datos y Endpoints Antes / Después (Secciones 1.2, 1.5, 4.1 y 14.3)

### 2.1 Tablas en Amazon RDS MySQL (`vehiculo_iot`)

| Tabla | Estado en 4.1 / 4.2 | Tratamiento en 4.3 | Registros Conservados / Iniciales |
|---|---|---|---|
| `vehiculos` | Existía | **SE MODIFICA** (`numero_serie`, `id_modelo`, `id_propietario`, `estado_comercial`, `soporte_autorizado`) | Unidad `#1` (Exhibición) + Unidad `#2` (Vendida a Comprador) |
| `comandos` | Existía | **SE REUTILIZA** | 18 comandos activos (9 por unidad) |
| `estado_vehiculo` | Existía | **SE REUTILIZA** | 2 estados activos |
| `historial_comandos` | Existía | **SE REUTILIZA (Intacto)** | **201+ registros históricos preservados** |
| `demos` | Existía | **SE MODIFICA** (`id_usuario`, `tipo_demo`: `FABRICA` / `PRIVADA`) | Demos de fábrica y privadas |
| `demo_movimientos` | Existía | **SE REUTILIZA** | Pasos ordenados con `duracion_ms` y `pausa_ms` |
| `roles` | No existía | **SE CREA** (`ADMIN`, `USUARIO`, `INVITADO`) | 3 roles comerciales |
| `usuarios` | No existía | **SE CREA** (con hash `PBKDF2-HMAC-SHA256`) | 3 cuentas iniciales + altas desde Admin |
| `modelos_comerciales`| No existía | **SE CREA** (separa Modelo Comercial de Unidad Física) | 2 modelos (`MOD-EXC-01`, `MOD-BAT-02`) |
| `sesiones_invitado` | No existía | **SE CREA** (reserva exclusiva con expiración UTC) | Sesiones temporales auditadas |
| `auditoria` | No existía | **SE CREA** (bitácora de seguridad sin secretos) | Registro continuo de eventos |

### 2.2 Matriz de Endpoints FastAPI (21 Servicios Originales + Ampliación 4.3)

| Grupo | Método y Ruta | Clasificación 4.3 | Control de Acceso |
|---|---|---|---|
| **Salud** | `GET /health` | **EXISTE / SE REUTILIZA** | Público (verifica API + ping real a RDS + conteo WSS) |
| **Estado** | `GET/PUT /vehiculos/{id}/estado` | **SE MODIFICA** | Exige JWT (`401`) + validación de propiedad/reserva (`403`) |
| **Historial** | `GET /vehiculos/{id}/historial` | **SE MODIFICA** | Exige JWT (`401`) + validación de propiedad/reserva (`403`) |
| **Control** | `POST /vehiculos/{id}/movimiento` | **SE MODIFICA** | Exige JWT + propiedad + filtro de comandos Invitado + soporte Admin |
| **Demos** | `GET /vehiculos/{id}/demos`, `POST .../iniciar`, `POST .../cancelar` | **SE MODIFICA** | Exige JWT + propiedad; bloqueado en modo Invitado (`403`) |
| **Catálogos 4.1** | CRUD `/vehiculos`, `/comandos`, `/demos` (21 SPs) | **SE CONSERVAN** | Compatibilidad total con los 21 procedimientos almacenados |
| **Auth 4.3** | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | **SE CREA** | Emisión y revocación en memoria de JWT HS256 |
| **Admin 4.3** | `GET /admin/dashboard`, CRUD `/admin/modelos`, `/admin/unidades`, `/admin/clientes`, `/admin/auditoria` | **SE CREA** | Exclusivo `ADMIN` (`403` para Usuario e Invitado); baja lógica de unidades |
| **Asignación 4.3**| `PATCH /admin/unidades/{id}/asignar` | **SE CREA** | Exclusivo `ADMIN`; conserva historial, revoca titular previo y audita |
| **Comprador 4.3** | `GET /mis-vehiculos`, `PATCH /mis-vehiculos/{id}/soporte` | **SE CREA** | Devuelve solo unidades propias y gestiona consentimiento de soporte |
| **Editor Demos** | `GET /editor-demos/vehiculo/{id}`, `POST/PUT/DELETE /editor-demos` | **SE CREA** | Valida capacidades por vehículo, rango `200–5000 ms` y dueño de la demo |
| **Invitado 4.3** | `GET /catalogo/publico`, `POST /invitado/sesiones/iniciar`, `GET .../actual`, `POST .../finalizar` | **SE CREA** | Reserva exclusiva (`409` si ocupada), timer y `DETENER (9)` al expirar |
| **WebSocket WSS** | `WSS /ws/vehiculo/{id}?token={jwt}` | **SE MODIFICA** | Valida JWT y propiedad (`4001`/`4003`); permite ESP32 físico en canal 1 |

---

## 3. Matriz de Evaluación Colaborativa P01 – P17 (Secciones 12.6 y 14.7)

| Código | Caso de Prueba | Rol Evaluado | Resultado | Evidencia / Comportamiento Verificado |
|---|---|---|---|---|
| **P01** | Login Admin y Dashboard | Administrador | **Correcto** | `POST /auth/login` -> `200 OK`; `GET /admin/dashboard` muestra KPIs reales desde RDS. |
| **P02** | Alta de modelo y unidad | Administrador | **Correcto** | `POST /admin/modelos` y `POST /admin/unidades` -> `201 Created` con número de serie único. |
| **P03** | Alta de cliente comprador | Administrador | **Correcto** | `POST /admin/clientes` -> `201 Created`; contraseña almacenada con hash `PBKDF2-SHA256`. |
| **P04** | Asignación de unidad | Administrador | **Correcto** | `PATCH /admin/unidades/{id}/asignar` -> `200 OK`; conserva historial y registra en `auditoria`. |
| **P05** | Aislamiento de comprador | Usuario | **Correcto** | `GET /mis-vehiculos` para `cliente1@gmail.com` devuelve únicamente su unidad asignada (`#2`). |
| **P06** | Control de unidad propia | Usuario | **Correcto** | `POST /vehiculos/2/movimiento` -> `200 OK`; joystick, botones y `DETENER (9)` operan el ESP32 físico. |
| **P07** | Suscripción WSS autenticada | Usuario / Admin | **Correcto** | `WSS /ws/vehiculo/{id}?token={jwt}` emite `CONEXION_ESTABLECIDA` y cancela socket al cambiar unidad. |
| **P08** | Historial de 10 individuales | Usuario / Admin | **Correcto** | `GET /vehiculos/{id}/historial` devuelve máx. 10 movimientos individuales sin pasos internos de DEMO. |
| **P09** | Demo persistente en RDS | Usuario / Admin | **Correcto** | `POST /editor-demos` guarda encabezado y pasos ordenados con validación de comandos y duración. |
| **P10** | Ejecución y cancelación DEMO | Usuario / Admin | **Correcto** | `POST /vehiculos/{id}/demos/{demo}/iniciar` (`202`) y `cancelar` (`200`); `DETENER` mantiene prioridad. |
| **P11** | Prueba temporal de Invitado | Invitado | **Correcto** | `POST /invitado/sesiones/iniciar` reserva por 90s; comando `#5` bloqueado (`403`), `#9` permitido (`200`). |
| **P12** | Rechazo de Admin a Invitado | Invitado / Anónimo | **Correcto** | `GET /admin/dashboard` sin token devuelve `401`; con token de Invitado o Usuario devuelve `403`. |
| **P13** | Rechazo de vehículo ajeno | Usuario / Admin | **Correcto** | Usuario en unidad `#1` ajena recibe `403` (anti-IDOR); Admin en unidad `#2` vendida sin soporte recibe `403`. |
| **P14** | Exclusividad de unidad | Invitado 2 | **Correcto** | Segundo `POST /invitado/sesiones/iniciar` sobre unidad `#1` ocupada devuelve `409 Conflict`. |
| **P15** | Reconexión y recuperación | Todos | **Correcto** | Al reconectar WSS, `wsService` actualiza badge a *En línea* y resincroniza estado e historial vía REST. |
| **P16** | Diseño Mobile First y créditos | Todos | **Correcto** | 3 pestañas responsivas, botones táctiles >=48px, 3 indicadores independientes, favicon y créditos del alumno. |
| **P17** | Bitácora de auditoría | Administrador | **Correcto** | `GET /admin/auditoria` lista logins, altas, asignaciones, bloqueos `403` y sesiones sin exponer secretos. |

---

## 4. Conclusiones Personales (Sección 16)

### 16.1 Integración de Administración a Control y Monitoreo y Comportamiento de los Tres Roles
La tercera vista (**ADMINISTRACIÓN**) se integró de manera modular dentro del mismo frontend (`index.html`, `main.js` y `administracion.js`) sin reconstruir ni perder ninguna funcionalidad previa de las prácticas 4.1 (**CONTROL**) y 4.2 (**MONITOREO**). Se conservaron el joystick virtual con retorno automático a `DETENER`, los botones táctiles, el ejecutor de secuencias DEMO, la tarjeta de último movimiento, la tabla de 10 registros individuales y los tres indicadores de salud. El uso de `sessionStorage` permitió abrir simultáneamente tres pestañas independientes para representar a la empresa (**Administrador**), al comprador (**Usuario**) y al prospecto (**Invitado**), comprobando que cada rol adapta tanto sus vistas como sus permisos reales en el servidor.

### 16.2 Decisiones del Modelo Relacional, Migraciones y Preservación de Historial
Antes de ejecutar cualquier sentencia DDL sobre Amazon RDS MySQL, se generó un respaldo completo (`backups/respaldo_4_2_previo_4_3.sql`) considerando que MySQL realiza *commit implícito* en operaciones `CREATE/ALTER TABLE`. Se decidió separar el concepto de **Modelo Comercial** (`modelos_comerciales`) del de **Unidad Física** (`vehiculos`), ampliando la tabla `vehiculos` con columnas anulables o con valor por defecto (`numero_serie`, `id_modelo`, `id_propietario`, `estado_comercial`, `soporte_autorizado`). Esta decisión evitó romper los 21 procedimientos almacenados existentes y permitió conservar intactos los **201 registros históricos** de `historial_comandos`. Asimismo, se prohibió el borrado físico de unidades con historial, implementando baja lógica (`activo = 0`, `estado_comercial = 'INACTIVO'`).

### 16.3 Reutilización de las 21 APIs, Autenticación, Roles y Autorización por Unidad (REST y WSS)
Se reutilizaron los endpoints originales de salud (`/health`), estado, historial, comandos y ejecución de demos, envolviéndolos con una capa de seguridad basada en tokens **JWT HS256** y control de acceso en dos niveles: primero **RBAC** (validación de rol `ADMIN`, `USUARIO` o `INVITADO`) y segundo **autorización por recurso (anti-IDOR/BOLA)** en `verificar_autorizacion_vehiculo()`. De esta forma, no basta con tener sesión iniciada: FastAPI y el handshake de WebSocket (`/ws/vehiculo/{id}?token=`) verifican que el usuario sea propietario de esa unidad específica o posea una reserva temporal activa, e impiden que el Administrador opere unidades vendidas sin el consentimiento explícito (`soporte_autorizado = 1`) del comprador.

### 16.4 Experiencia de la Prueba Colaborativa y Correcciones Aplicadas
Durante las pruebas de los tres roles se detectaron y corrigieron dos situaciones clave con el hardware físico: primero, el filtro de autenticación WSS rechazaba inicialmente al microcontrolador ESP32 porque éste no enviaba token JWT como un navegador; se ajustó el handshake en `app/main.py` para autenticar estrictamente a los navegadores (que envían cabecera `Origin`) y permitir la conexión directa del ESP32 en el canal físico. Segundo, dado que en el laboratorio se cuenta con un único carrito físico suscrito al canal `#1`, cuando el comprador operaba su unidad vendida `#2` la orden se guardaba en RDS pero no movía el hardware; se implementó en `connection_manager.py` una retransmisión controlada hacia el canal físico `#1`, logrando que el comprador mueva el vehículo real sin perder el aislamiento lógico y de base de datos entre la Unidad `#1` (Exhibición) y la Unidad `#2` (Vendida).

### 16.5 Evaluación de Seguridad en Invitados, Demos, Reconexión y Mejora Técnica Futura
El sistema de sesiones temporales para **Invitados** garantiza seguridad física y operativa mediante tres mecanismos: reserva exclusiva en base de datos que rechaza con `409 Conflict` cualquier intento de control simultáneo, lista blanca de comandos básicos (bloqueando con `403` movimientos de brazo o secuencias completas) y una tarea asíncrona en el backend que, al expirar el tiempo límite o cerrarse la sesión, libera la unidad y emite automáticamente el comando prioritario `DETENER (9)` por WSS. Como mejora técnica concreta para una versión futura, se propone incorporar **autenticación mutua por dispositivo (mTLS o token HMAC firmado en la NVRAM del ESP32)** junto con un mensaje periódico de *heartbeat* desde el microcontrolador cada 5 segundos, de modo que el frontend pueda distinguir con certeza criptográfica entre *"sesión WSS del navegador activa"* y *"microcontrolador físico energizado y en línea"*.
