# Plataforma Comercial Multiusuario IoT (4.1 Control · 4.2 Monitoreo · 4.3 Administración)

**Alumno:** Alan Santiago Rodríguez  
**Matrícula:** 22200767  
**Año:** 2026  
**Repositorio GitHub:** [https://github.com/AlanSR25/api-vehiculo-iot](https://github.com/AlanSR25/api-vehiculo-iot)  
**Aplicación Web Pública (GitHub Pages):** [https://alansr25.github.io/api-vehiculo-iot/](https://alansr25.github.io/api-vehiculo-iot/)  

---

## 1. Enlaces Públicos y Contratos Activos

* **Frontend Integrado (Control + Monitoreo + Administración)**: `https://alansr25.github.io/api-vehiculo-iot/`
* **Base API HTTPS (Cloudflare TLS)**: `https://platinum-nissan-orlando-proved.trycloudflare.com`
* **Documentación Swagger / OpenAPI**: `https://platinum-nissan-orlando-proved.trycloudflare.com/docs`
* **Canal WebSocket Seguro Autenticado (WSS)**: `wss://platinum-nissan-orlando-proved.trycloudflare.com/ws/vehiculo/{id_vehiculo}?token={jwt}`
* **Diagnóstico de Salud (API + RDS)**: `https://platinum-nissan-orlando-proved.trycloudflare.com/health`

---

## 2. Modelo de Negocio y Roles (RBAC + Autorización por Recurso)

| Rol | Alcance en Frontend | Seguridad Aplicada en FastAPI y WSS |
|---|---|---|
| **ADMIN** (Empresa) | Dashboard KPI real, CRUD de Modelos Comerciales, CRUD de Unidades Físicas, Clientes, Asignaciones, Demos de Fábrica y Bitácora de Auditoría. | Acceso total a `/admin/*`. **Bloqueado (`403`)** para operar físicamente unidades vendidas a compradores salvo autorización explícita de soporte (`soporte_autorizado = 1`). |
| **USUARIO** (Comprador) | **«Mis Vehículos»**, Control, Monitoreo, switch de autorización de soporte técnico y Editor Visual de Demos Privadas. | Aislamiento estricto anti-IDOR/BOLA: solo consulta/opera unidades donde `id_propietario == user.id`. Cualquier otro ID devuelve `403 Forbidden` tanto en REST como en WSS (`4003`). |
| **INVITADO** (Prospecto) | **«Prueba nuestros vehículos IoT»**: catálogo público de modelos y reserva exclusiva temporal (90s) de unidades en estado `EXHIBICION`. | Reserva exclusiva en RDS (`409 Conflict` si otro invitado la ocupa). Comandos restringidos (`1,2,3,4,7,9`). Al expirar o finalizar, se emite `DETENER (9)` automático por WSS. |

---

## 3. Migración Incremental de Base de Datos (V4.3.0)

* **Respaldo previo**: `backups/respaldo_4_2_previo_4_3.sql` generado en EC2 antes de cualquier DDL.
* **Scripts versionados**:
  * [`migrations/V4.3.0__ampliacion_comercial_up.sql`](migrations/V4.3.0__ampliacion_comercial_up.sql)
  * [`migrations/V4.3.0__ampliacion_comercial_down.sql`](migrations/V4.3.0__ampliacion_comercial_down.sql)
  * [`migrations/apply_v4_3_0.py`](migrations/apply_v4_3_0.py) (aplicador idempotente)
* **Preservación de datos**: Las 6 tablas originales y los **201 registros históricos** de `historial_comandos` se conservaron intactos.
* **Tablas agregadas**: `roles`, `usuarios`, `modelos_comerciales`, `sesiones_invitado`, `auditoria`.
* **Columnas incrementales**: `vehiculos` (`numero_serie`, `id_modelo`, `id_propietario`, `estado_comercial`, `soporte_autorizado`) y `demos` (`id_usuario`, `tipo_demo`).

---

## 4. Endpoints Nuevos de la Práctica 4.3 (Ampliación sobre las 21 APIs)

* **Autenticación**: `POST /auth/login`, `POST /auth/logout` (revocación real), `GET /auth/me`.
* **Administración (Solo ADMIN)**: `GET /admin/dashboard`, `GET/POST/PUT /admin/modelos`, `GET/POST/PUT/DELETE /admin/unidades` (baja lógica), `PATCH /admin/unidades/{id}/asignar`, `GET/POST/PUT /admin/clientes`, `GET /admin/auditoria`.
* **Comprador**: `GET /mis-vehiculos`, `PATCH /mis-vehiculos/{id}/soporte`.
* **Editor Visual de Demos**: `GET /editor-demos/vehiculo/{id}`, `POST /editor-demos`, `PUT /editor-demos/{id}`, `DELETE /editor-demos/{id}`.
* **Invitado y Exhibición**: `GET /catalogo/publico`, `POST /invitado/sesiones/iniciar`, `GET /invitado/sesiones/actual`, `POST /invitado/sesiones/finalizar`.

---

## 5. Variables de Entorno (Solo Nombres)

`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_POOL_SIZE`, `JWT_SECRET`, `JWT_EXPIRES_MINUTES`, `INVITADO_MAX_SECONDS`.  
*(Ninguna credencial real se almacena en el repositorio ni en el frontend).*

---

## 6. Matriz de Pruebas Verificadas (P01 – P17)

Suite automatizada reproducible en [`tests/test_seguridad_4_3.py`](tests/test_seguridad_4_3.py):

| ID | Prueba | Resultado |
|---|---|---|
| P01 | Login Admin + Dashboard KPIs reales desde RDS | **Correcto (200)** |
| P02 | Alta de modelo comercial y unidad física con serie única | **Correcto (201)** |
| P03 | Alta de cliente comprador con hash PBKDF2-SHA256 | **Correcto (201)** |
| P04 | Asignación/reasignación de unidad conservando historial | **Correcto (200)** |
| P05 | Aislamiento de comprador («Mis Vehículos» solo devuelve propios) | **Correcto (200)** |
| P06 | Control de unidad propia (Joystick, botones y DETENER prioritario) | **Correcto (200)** |
| P07 | Canal WSS autenticado por token y filtrado por `id_vehiculo` | **Correcto** |
| P08 | Historial de 10 movimientos individuales persistidos (sin pasos DEMO) | **Correcto (200)** |
| P09 | Editor visual de demos persistente en RDS (pasos ordenados y duración) | **Correcto (201)** |
| P10 | Ejecución y cancelación segura de DEMO con prioridad de DETENER | **Correcto (202/200)** |
| P11 | Catálogo público + Reserva temporal de Invitado con comandos restringidos | **Correcto (201/403)** |
| P12 | Rechazo de acceso a Administración a Invitado/Usuario y 401 sin token | **Correcto (401/403)** |
| P13 | Rechazo de vehículo ajeno (IDOR) y de Admin sin soporte en unidad vendida | **Correcto (403)** |
| P14 | Exclusividad de control: segunda sesión de Invitado bloqueada | **Correcto (409)** |
| P15 | Reconexión WSS y resincronización automática vía REST | **Correcto** |
| P16 | Diseño Mobile First responsivo en 3 vistas + 3 indicadores + créditos | **Correcto** |
| P17 | Registro y consulta de Bitácora de Auditoría en RDS | **Correcto (200)** |

---

## 7. Créditos

* **Desarrollado por:** Alan Santiago Rodríguez (Matrícula: 22200767) · 2026
