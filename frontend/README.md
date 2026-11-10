# Aplicación Web de Control IoT · Vehículo Excavadora

Aplicación web responsiva (**Mobile First**) desarrollada con **HTML5 semántico, CSS3, Bootstrap 5 y JavaScript modular (ES6+)** para el control en tiempo real de un vehículo IoT desplegado en **Amazon EC2 (FastAPI)** y **Amazon RDS (MySQL)** con eventos WebSocket (**WSS**).

Publicada de forma segura en **GitHub Pages**.

---

## 1. Arquitectura y Flujo de Datos

```
[ Navegador / Celular (GitHub Pages) ]
      │             │
Fetch │             │ WebSocket (WSS)
REST  │             │ Eventos en vivo
      ▼             ▼
[ Amazon EC2 (FastAPI + Uvicorn) ] ── (SQL / Stored Procedures) ──► [ Amazon RDS (MySQL) ]
      │
      ▼ (WSS Broadcast)
[ Cliente Externo / Thunder Client / Postman / ESP32 ]
```

---

## 2. Características Implementadas

1. **Mobile First & Responsividad**: Adaptada para pantallas táctiles de celulares, tabletas y computadoras.
2. **Joystick Virtual Táctil**: Control direccional con Pointer Events (Avanzar, Retroceder, Izquierda, Derecha). Al soltar, envía **DETENER (9)** automáticamente sin ráfagas innecesarias.
3. **Botón DETENER Prioritario**: Acción visual prominente para frenar de inmediato el vehículo y detener cualquier DEMO o secuencia activa.
4. **Controles Táctiles Auxiliares**:
   * Subir Brazo (Comando 5 / Q6)
   * Bajar Brazo (Comando 6 / Q3)
   * Luz On/Off (Comando 7 / Q5)
   * Grabación interactiva (Comando 8)
5. **Panel de Tres Indicadores de Conexión Reales**:
   * **WebSocket WSS**: *En línea*, *Conectando/Reconectando* o *Desconectado* (refleja la sesión activa del navegador con el servidor WSS).
   * **API AWS (EC2)**: *Disponible*, *Comprobando* o *No disponible* (sondeo periódico controlado a `/health`).
   * **Amazon RDS**: *Disponible*, *No disponible* o *Sin verificar* (diagnóstico real de base de datos retornado de forma segura por el backend).
6. **Selector y Ejecución de DEMO**: Consulta de secuencias existentes en base de datos e inicio/cancelación en tiempo real.
7. **Favicon Propio y Créditos**: Favicon SVG temático y pie de página con créditos del estudiante.

---

## 3. Estructura del Proyecto Frontend

```
frontend/
├── index.html                   # Interfaz semántica con Bootstrap 5
├── assets/
│   ├── css/
│   │   └── styles.css           # Estilos personalizados, joystick y estados
│   ├── icons/
│   │   └── favicon.svg          # Favicon original del proyecto IoT
│   └── js/
│       ├── config.js            # Configuración de URLs y contratos (sin secretos)
│       ├── main.js              # Inicializador y orquestador UI
│       ├── components/
│       │   └── joystick.js      # Componente modular del joystick táctil
│       ├── services/
│       │   ├── apiService.js    # Cliente HTTP con Fetch, async/await y timeout
│       │   └── wsService.js     # Cliente WebSocket con reconexión automática
│       └── state/
│           └── appState.js      # Estado reactivo compartido
```

---

## 4. Instrucciones para Ejecución Local

1. Abre Visual Studio Code en la carpeta del proyecto.
2. Abre el archivo `frontend/index.html`.
3. Haz clic derecho y selecciona **"Open with Live Server"** (o usa cualquier servidor web estático local como `python -m http.server` en la carpeta `frontend`).
4. Abre en tu navegador `http://localhost:5500` (o el puerto asignado).

> [!NOTE]
> Al conectarse por primera vez a la API de AWS (`https://44.194.225.196:8000`), asegúrate de aceptar el certificado autofirmado en una pestaña del navegador visitando `https://44.194.225.196:8000/docs` una sola vez.

---

## 5. Guía para Publicar en GitHub Pages

1. Inicializa el repositorio Git en la carpeta del proyecto si no lo tienes:
   ```bash
   git add .
   git commit -m "feat: Aplicacion web de control IoT completa con joystick y WSS"
   ```
2. Sube tu código a tu repositorio de GitHub:
   ```bash
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   git branch -M main
   git push -u origin main
   ```
3. En GitHub, entra a **Settings** > **Pages**.
4. En **Build and deployment > Branch**, selecciona:
   * Branch: `main`
   * Folder: `/ (root)` (si publicas desde la raíz) o crea un subdirectorio según tu preferencia.
5. Haz clic en **Save**. En un par de minutos tu sitio estará en vivo en:
   `https://TU_USUARIO.github.io/TU_REPOSITORIO/`

---

## 6. Verificación Independiente por WebSocket (Postman / Thunder Client)

1. Abre **Postman** o **Thunder Client** y crea una nueva petición de tipo **WebSocket**.
2. Conéctate a la URL:
   ```
   wss://44.194.225.196:8000/ws/vehiculo/1
   ```
3. Al conectar, recibirás el evento de estado inicial:
   ```json
   {
     "evento": "CONEXION_ESTABLECIDA",
     "id_vehiculo": 1,
     "estado": { ... }
   }
   ```
4. Acciona el **Joystick** o los botones en tu aplicación web y observa cómo llegan de inmediato los mensajes correspondientes al cliente independiente:
   ```json
   {
     "evento": "MOVIMIENTO_INDIVIDUAL",
     "id_vehiculo": 1,
     "codigo": 1,
     "comando": "AVANZAR",
     "origen": "FRONTEND-WEB"
   }
   ```

