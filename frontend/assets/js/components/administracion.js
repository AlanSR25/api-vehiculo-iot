/**
 * administracion.js - Módulo completo de la Práctica 4.3 (Administración Comercial IoT)
 * - ADMIN: Dashboard KPI, CRUD Modelos, CRUD Unidades, Asignaciones, Clientes y Auditoría.
 * - USUARIO: "Mis Vehículos", autorización de soporte técnico y Editor Visual de Demos Privadas.
 * - INVITADO: "Prueba nuestros vehículos IoT" (Catálogo público y reserva exclusiva temporal).
 */

import { apiService } from "../services/apiService.js?v=20261125b";
import { formatearFechaHora } from "./monitoreo.js?v=20261125b";

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

class AdministracionManager {
  constructor() {
    this.onSelectVehicle = null;
    this.onGuestSessionStarted = null;
    this.onDemosChanged = null;
    this.onUnitCommandsUpdated = null;
    this.modalComandosUnidad = null;
    this.comandosEditandoVehiculoId = null;

    this.modelosCache = [];
    this.clientesCache = [];
    this.unidadesCache = [];
    this.editorVehiculoId = null;
    this.editorComandos = [];
    this.editorPasos = [];
    this.editorDemoId = null;

    this.dom = {
      // Contenedores por rol
      panelAdmin: document.getElementById("panelAdminRol"),
      panelUsuario: document.getElementById("panelUsuarioRol"),
      panelInvitado: document.getElementById("panelInvitadoRol"),
      panelEditorDemos: document.getElementById("panelEditorDemos"),

      // Feedback
      adminAlert: document.getElementById("adminFeedbackAlert"),

      // Dashboard Admin
      kpiModelos: document.getElementById("kpiModelos"),
      kpiUnidades: document.getElementById("kpiUnidades"),
      kpiVendidas: document.getElementById("kpiVendidas"),
      kpiExhibicion: document.getElementById("kpiExhibicion"),
      kpiClientes: document.getElementById("kpiClientes"),
      kpiDemos: document.getElementById("kpiDemos"),
      kpiHistorico: document.getElementById("kpiHistorico"),
      kpiWss: document.getElementById("kpiWss"),

      // Tablas Admin
      tbodyModelos: document.getElementById("tbodyModelos"),
      tbodyUnidades: document.getElementById("tbodyUnidades"),
      tbodyClientes: document.getElementById("tbodyClientes"),
      tbodyAuditoria: document.getElementById("tbodyAuditoria"),

      // Formularios Admin
      formNuevoModelo: document.getElementById("formNuevoModelo"),
      formNuevaUnidad: document.getElementById("formNuevaUnidad"),
      selectUnidadModelo: document.getElementById("unidadModeloSelect"),
      selectUnidadPropietario: document.getElementById("unidadPropietarioSelect"),
      formNuevoCliente: document.getElementById("formNuevoCliente"),
      btnRefrescarAdmin: document.getElementById("btnRefrescarAdmin"),

      // Usuario: Mis Vehículos
      misVehiculosGrid: document.getElementById("misVehiculosGrid"),

      // Editor de Demos
      editorSelectVehiculo: document.getElementById("editorDemoVehiculoSelect"),
      editorListaDemos: document.getElementById("editorListaDemos"),
      editorNombre: document.getElementById("editorDemoNombre"),
      editorDescripcion: document.getElementById("editorDemoDescripcion"),
      editorSelectComando: document.getElementById("editorPasoComando"),
      editorDuracion: document.getElementById("editorPasoDuracion"),
      editorPausa: document.getElementById("editorPasoPausa"),
      btnAgregarPaso: document.getElementById("btnAgregarPasoDemo"),
      editorPasosBody: document.getElementById("editorPasosBody"),
      editorDuracionTotal: document.getElementById("editorDuracionTotal"),
      btnGuardarDemo: document.getElementById("btnGuardarDemo"),
      btnNuevaDemo: document.getElementById("btnLimpiarEditorDemo"),

      // Invitado: Catálogo Público
      catalogoModelosGrid: document.getElementById("catalogoModelosGrid"),
      catalogoExhibicionGrid: document.getElementById("catalogoExhibicionGrid"),
      inputNombreInvitado: document.getElementById("inputNombreInvitado"),
      btnRefrescarCatalogo: document.getElementById("btnRefrescarCatalogo"),

      // Modal Editar Comandos por Unidad
      modalComandosEl: document.getElementById("modalComandosUnidad"),
      modalComandosSubtitulo: document.getElementById("modalComandosUnidadSubtitulo"),
      modalComandosLista: document.getElementById("modalComandosLista"),
      btnGuardarComandosUnidad: document.getElementById("btnGuardarComandosUnidad"),
    };

    if (this.dom.modalComandosEl && window.bootstrap?.Modal) {
      this.modalComandosUnidad = new window.bootstrap.Modal(this.dom.modalComandosEl);
    }

    this._bindEvents();
  }

  showFeedback(message, type = "success") {
    if (!this.dom.adminAlert) return;
    this.dom.adminAlert.className = `alert alert-${type} py-2 small mb-3`;
    this.dom.adminAlert.textContent = message;
    this.dom.adminAlert.classList.remove("d-none");
    setTimeout(() => this.dom.adminAlert?.classList.add("d-none"), 5000);
  }

  _bindEvents() {
    this.dom.btnRefrescarAdmin?.addEventListener("click", () => this.cargarAdminCompleto());
    this.dom.btnRefrescarCatalogo?.addEventListener("click", () => this.cargarCatalogoPublico());

    // Crear Modelo Comercial
    this.dom.formNuevoModelo?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await apiService.crearModelo({
          codigo_modelo: fd.get("codigo_modelo"),
          nombre: fd.get("nombre"),
          categoria: fd.get("categoria"),
          descripcion: fd.get("descripcion"),
          comandos_soportados: fd.get("comandos_soportados"),
          precio_referencia: Number(fd.get("precio_referencia") || 0),
          imagen_icono: "bi-truck-front",
        });
        e.target.reset();
        this.showFeedback("Modelo comercial registrado en Amazon RDS.", "success");
        await this.cargarAdminCompleto();
      } catch (err) {
        this.showFeedback(`Error al crear modelo: ${err.message}`, "danger");
      }
    });

    // Crear Unidad Física
    this.dom.formNuevaUnidad?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const propRaw = fd.get("id_propietario");
      try {
        await apiService.crearUnidad({
          nombre: fd.get("nombre"),
          numero_serie: fd.get("numero_serie"),
          id_modelo: Number(fd.get("id_modelo")),
          microcontrolador: fd.get("microcontrolador") || "ESP32",
          descripcion: fd.get("descripcion") || "",
          estado_comercial: fd.get("estado_comercial"),
          id_propietario: propRaw ? Number(propRaw) : null,
        });
        e.target.reset();
        this.showFeedback("Unidad física registrada con catálogo de comandos del modelo.", "success");
        await this.cargarAdminCompleto();
      } catch (err) {
        this.showFeedback(`Error al crear unidad: ${err.message}`, "danger");
      }
    });

    // Crear Cliente / Usuario
    this.dom.formNuevoCliente?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await apiService.crearCliente({
          nombre_completo: fd.get("nombre_completo"),
          correo: fd.get("correo"),
          password: fd.get("password"),
          telefono: fd.get("telefono") || null,
          rol_codigo: fd.get("rol_codigo"),
        });
        e.target.reset();
        this.showFeedback("Cuenta de usuario creada correctamente.", "success");
        await this.cargarAdminCompleto();
      } catch (err) {
        this.showFeedback(`Error al crear usuario: ${err.message}`, "danger");
      }
    });

    // Editor de Demos
    this.dom.editorSelectVehiculo?.addEventListener("change", (e) => {
      this.cargarEditorDemosVehiculo(Number(e.target.value));
    });

    this.dom.btnAgregarPaso?.addEventListener("click", () => {
      const cmdId = Number(this.dom.editorSelectComando?.value);
      const dur = Number(this.dom.editorDuracion?.value || 1500);
      const pausa = Number(this.dom.editorPausa?.value || 250);
      if (!cmdId) return;
      if (this.editorPasos.length >= 15) {
        this.showFeedback("Máximo 15 pasos por secuencia DEMO.", "warning");
        return;
      }
      const cmdObj = this.editorComandos.find((c) => c.id_comando === cmdId);
      this.editorPasos.push({
        id_comando: cmdId,
        comando: cmdObj ? cmdObj.nombre : `#${cmdId}`,
        codigo: cmdObj ? cmdObj.codigo : "",
        duracion_ms: Math.min(5000, Math.max(200, dur)),
        pausa_ms: Math.min(3000, Math.max(0, pausa)),
      });
      this._renderEditorPasos();
    });

    this.dom.btnNuevaDemo?.addEventListener("click", () => {
      this.editorDemoId = null;
      this.editorPasos = [];
      if (this.dom.editorNombre) this.dom.editorNombre.value = "";
      if (this.dom.editorDescripcion) this.dom.editorDescripcion.value = "";
      this._renderEditorPasos();
    });

    this.dom.btnGuardarDemo?.addEventListener("click", async () => {
      const nombre = this.dom.editorNombre?.value.trim();
      const descripcion = this.dom.editorDescripcion?.value.trim() || "";
      if (!this.editorVehiculoId || !nombre || this.editorPasos.length === 0) {
        this.showFeedback("Ingresa un nombre y al menos 1 paso para guardar la DEMO.", "warning");
        return;
      }
      const payload = {
        id_vehiculo: this.editorVehiculoId,
        nombre,
        descripcion,
        pasos: this.editorPasos.map((p) => ({
          id_comando: p.id_comando,
          duracion_ms: p.duracion_ms,
          pausa_ms: p.pausa_ms,
        })),
      };
      try {
        if (this.editorDemoId) {
          await apiService.editarDemoCompleta(this.editorDemoId, payload);
          this.showFeedback("DEMO actualizada en Amazon RDS.", "success");
        } else {
          await apiService.crearDemoCompleta(payload);
          this.showFeedback("Nueva DEMO guardada en Amazon RDS.", "success");
        }
        this.editorDemoId = null;
        this.editorPasos = [];
        if (this.dom.editorNombre) this.dom.editorNombre.value = "";
        if (this.dom.editorDescripcion) this.dom.editorDescripcion.value = "";
        this._renderEditorPasos();
        await this.cargarEditorDemosVehiculo(this.editorVehiculoId);
        if (this.onDemosChanged) this.onDemosChanged(this.editorVehiculoId);
      } catch (err) {
        this.showFeedback(`Error al guardar DEMO: ${err.message}`, "danger");
      }
    });

    // Guardar Comandos Habilitados / Bloqueados de una Unidad Física
    this.dom.btnGuardarComandosUnidad?.addEventListener("click", async () => {
      if (!this.comandosEditandoVehiculoId || !this.dom.modalComandosLista) return;
      const checks = this.dom.modalComandosLista.querySelectorAll(".check-comando-unidad:checked");
      const codigos = Array.from(checks).map((el) => Number(el.value));
      if (!codigos.includes(9)) codigos.push(9);
      try {
        await apiService.actualizarComandosUnidadAdmin(this.comandosEditandoVehiculoId, codigos);
        this.modalComandosUnidad?.hide();
        this.showFeedback(`Movimientos de Unidad #${this.comandosEditandoVehiculoId} actualizados en RDS.`, "success");
        if (this.onUnitCommandsUpdated) this.onUnitCommandsUpdated(this.comandosEditandoVehiculoId);
        await this.cargarAdminCompleto();
      } catch (err) {
        this.showFeedback(`Error al actualizar movimientos: ${err.message}`, "danger");
      }
    });
  }

  async renderPorRol(user, activeVehicleId = null) {
    const rol = user?.rol || "ANONIMO";

    this.dom.panelAdmin?.classList.toggle("d-none", rol !== "ADMIN");
    this.dom.panelUsuario?.classList.toggle("d-none", rol !== "USUARIO");
    this.dom.panelEditorDemos?.classList.toggle("d-none", rol !== "ADMIN" && rol !== "USUARIO");
    this.dom.panelInvitado?.classList.toggle("d-none", rol === "ADMIN" || rol === "USUARIO");

    if (rol === "ADMIN") {
      await this.cargarAdminCompleto();
      const vId = activeVehicleId || this.unidadesCache[0]?.id_vehiculo || 1;
      await this.cargarEditorDemosVehiculo(vId);
    } else if (rol === "USUARIO") {
      const unidades = await this.cargarMisVehiculos(activeVehicleId);
      const vId = activeVehicleId || unidades[0]?.id_vehiculo;
      if (vId) await this.cargarEditorDemosVehiculo(vId);
    } else {
      await this.cargarCatalogoPublico();
    }
  }

  // =========================================================================
  // ADMIN: DASHBOARD + INVENTARIO + CLIENTES + AUDITORÍA
  // =========================================================================
  async cargarAdminCompleto() {
    try {
      const [dash, modelos, unidades, clientes, auditoria] = await Promise.all([
        apiService.getDashboard(),
        apiService.getModelos(),
        apiService.getUnidadesAdmin(),
        apiService.getClientes(),
        apiService.getAuditoria(40),
      ]);

      this.modelosCache = modelos || [];
      this.unidadesCache = unidades || [];
      this.clientesCache = clientes || [];

      // KPIs
      const m = dash?.metricas || {};
      if (this.dom.kpiModelos) this.dom.kpiModelos.textContent = m.total_modelos ?? 0;
      if (this.dom.kpiUnidades) this.dom.kpiUnidades.textContent = m.total_unidades ?? 0;
      if (this.dom.kpiVendidas) this.dom.kpiVendidas.textContent = m.unidades_vendidas ?? 0;
      if (this.dom.kpiExhibicion) this.dom.kpiExhibicion.textContent = m.unidades_exhibicion ?? 0;
      if (this.dom.kpiClientes) this.dom.kpiClientes.textContent = m.total_clientes ?? 0;
      if (this.dom.kpiDemos) this.dom.kpiDemos.textContent = m.total_demos ?? 0;
      if (this.dom.kpiHistorico) this.dom.kpiHistorico.textContent = m.total_movimientos_historicos ?? 0;
      const totalWss = Object.values(dash?.sesiones_wss_navegador || {}).reduce((a, b) => a + b, 0);
      if (this.dom.kpiWss) this.dom.kpiWss.textContent = totalWss;

      this._renderSelectoresAdmin();
      this._renderTablaModelos();
      this._renderTablaUnidades();
      this._renderTablaClientes();
      this._renderTablaAuditoria(auditoria || []);

      // Poblar selector del editor de demos
      if (this.dom.editorSelectVehiculo) {
        this.dom.editorSelectVehiculo.innerHTML = this.unidadesCache
          .filter((u) => u.activo)
          .map((u) => `<option value="${u.id_vehiculo}">#${u.id_vehiculo} · ${escapeHtml(u.nombre)} (${u.estado_comercial})</option>`)
          .join("");
      }
    } catch (err) {
      this.showFeedback(`Error al cargar panel administrativo: ${err.message}`, "danger");
    }
  }

  _renderSelectoresAdmin() {
    if (this.dom.selectUnidadModelo) {
      this.dom.selectUnidadModelo.innerHTML = this.modelosCache
        .filter((m) => m.activo)
        .map((m) => `<option value="${m.id_modelo}">${escapeHtml(m.codigo_modelo)} - ${escapeHtml(m.nombre)}</option>`)
        .join("");
    }
    if (this.dom.selectUnidadPropietario) {
      const buyers = this.clientesCache.filter((c) => c.activo);
      this.dom.selectUnidadPropietario.innerHTML =
        `<option value="">-- Sin propietario (Inventario / Exhibición) --</option>` +
        buyers.map((c) => `<option value="${c.id_usuario}">${escapeHtml(c.nombre_completo)} (${escapeHtml(c.correo)})</option>`).join("");
    }
  }

  _renderTablaModelos() {
    if (!this.dom.tbodyModelos) return;
    this.dom.tbodyModelos.innerHTML = this.modelosCache
      .map(
        (m) => `
      <tr>
        <td><span class="badge bg-info-subtle text-info">${escapeHtml(m.codigo_modelo)}</span></td>
        <td class="fw-semibold text-white">${escapeHtml(m.nombre)}</td>
        <td><small class="text-secondary">${escapeHtml(m.categoria)}</small></td>
        <td><code>${escapeHtml(m.comandos_soportados)}</code></td>
        <td>$${Number(m.precio_referencia || 0).toLocaleString("es-MX")}</td>
        <td><span class="badge bg-secondary">${m.total_unidades || 0}</span></td>
      </tr>`
      )
      .join("");
  }

  _renderTablaUnidades() {
    if (!this.dom.tbodyUnidades) return;
    const clientesOpts = (selectedId) =>
      `<option value="">Sin propietario</option>` +
      this.clientesCache
        .filter((c) => c.activo)
        .map((c) => `<option value="${c.id_usuario}" ${Number(selectedId) === Number(c.id_usuario) ? "selected" : ""}>${escapeHtml(c.correo)}</option>`)
        .join("");

    this.dom.tbodyUnidades.innerHTML = this.unidadesCache
      .map((u) => {
        const badgeEstado =
          u.estado_comercial === "EXHIBICION"
            ? "bg-info text-dark"
            : u.estado_comercial === "VENDIDO"
            ? "bg-success"
            : u.estado_comercial === "INACTIVO"
            ? "bg-secondary"
            : "bg-warning text-dark";
        return `
        <tr>
          <td><strong>#${u.id_vehiculo}</strong><br><small class="text-secondary">${escapeHtml(u.numero_serie || "-")}</small></td>
          <td class="text-white fw-semibold">${escapeHtml(u.nombre)}<br><small class="text-secondary">${escapeHtml(u.modelo_comercial_nombre || u.modelo)}</small></td>
          <td><span class="badge ${badgeEstado}">${escapeHtml(u.estado_comercial)}</span>${u.soporte_autorizado ? ' <span class="badge bg-primary">Soporte OK</span>' : ""}</td>
          <td>
            <div class="d-flex gap-1 align-items-center">
              <select class="form-select form-select-sm bg-dark text-white border-secondary select-asignar-prop" data-id="${u.id_vehiculo}" style="min-width:155px">
                ${clientesOpts(u.id_propietario)}
              </select>
              <select class="form-select form-select-sm bg-dark text-white border-secondary select-asignar-estado" data-id="${u.id_vehiculo}" style="min-width:115px">
                ${["EXHIBICION", "DISPONIBLE", "VENDIDO", "MANTENIMIENTO"]
                  .map((st) => `<option value="${st}" ${u.estado_comercial === st ? "selected" : ""}>${st}</option>`)
                  .join("")}
              </select>
              <button class="btn btn-sm btn-outline-success btn-guardar-asignacion" data-id="${u.id_vehiculo}" title="Guardar asignación">
                <i class="bi bi-check2"></i>
              </button>
            </div>
          </td>
          <td><span class="badge bg-dark border border-secondary">${u.total_historial || 0} movs</span></td>
          <td>
            <div class="d-flex gap-1">
              <button class="btn btn-sm btn-outline-warning btn-editar-comandos" data-id="${u.id_vehiculo}" data-nombre="${escapeHtml(u.nombre)}" title="Editar / bloquear movimientos">
                <i class="bi bi-sliders"></i>
              </button>
              <button class="btn btn-sm btn-outline-info btn-operar-unidad" data-id="${u.id_vehiculo}" data-nombre="${escapeHtml(u.nombre)}" title="Seleccionar en Control/Monitoreo">
                <i class="bi bi-controller"></i>
              </button>
              ${u.activo ? `<button class="btn btn-sm btn-outline-danger btn-baja-unidad" data-id="${u.id_vehiculo}" title="Baja lógica (conserva historial)"><i class="bi bi-archive"></i></button>` : ""}
            </div>
          </td>
        </tr>`;
      })
      .join("");

    // Bind eventos dinámicos
    this.dom.tbodyUnidades.querySelectorAll(".btn-guardar-asignacion").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.id);
        const propSel = this.dom.tbodyUnidades.querySelector(`.select-asignar-prop[data-id="${id}"]`);
        const estSel = this.dom.tbodyUnidades.querySelector(`.select-asignar-estado[data-id="${id}"]`);
        const idProp = propSel?.value ? Number(propSel.value) : null;
        const estado = estSel?.value || (idProp ? "VENDIDO" : "EXHIBICION");
        try {
          await apiService.asignarUnidad(id, { id_propietario: idProp, estado_comercial: estado });
          this.showFeedback(`Unidad #${id} actualizada y auditada correctamente.`, "success");
          await this.cargarAdminCompleto();
        } catch (err) {
          this.showFeedback(`Error al asignar unidad: ${err.message}`, "danger");
        }
      });
    });

    this.dom.tbodyUnidades.querySelectorAll(".btn-baja-unidad").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.id);
        if (!confirm(`¿Dar de baja lógica la unidad #${id}? Se conservará todo su historial en RDS.`)) return;
        try {
          await apiService.bajaLogicaUnidad(id);
          this.showFeedback(`Unidad #${id} dada de baja lógicamente.`, "warning");
          await this.cargarAdminCompleto();
        } catch (err) {
          this.showFeedback(`Error: ${err.message}`, "danger");
        }
      });
    });

    this.dom.tbodyUnidades.querySelectorAll(".btn-operar-unidad").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.onSelectVehicle) this.onSelectVehicle(Number(btn.dataset.id), btn.dataset.nombre, true);
      });
    });

    this.dom.tbodyUnidades.querySelectorAll(".btn-editar-comandos").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.id);
        const nombre = btn.dataset.nombre || `Unidad #${id}`;
        await this.abrirModalComandosUnidad(id, nombre);
      });
    });
  }

  async abrirModalComandosUnidad(idVehiculo, nombreUnidad) {
    if (!this.dom.modalComandosLista) return;
    this.comandosEditandoVehiculoId = idVehiculo;
    if (this.dom.modalComandosSubtitulo) {
      this.dom.modalComandosSubtitulo.textContent = `Unidad #${idVehiculo} (${nombreUnidad}): marca los movimientos permitidos o desmarca para bloquear.`;
    }
    this.dom.modalComandosLista.innerHTML = `<div class="text-center text-secondary py-3 small">Cargando comandos desde RDS...</div>`;
    this.modalComandosUnidad?.show();

    try {
      const data = await apiService.getComandosUnidadAdmin(idVehiculo);
      const comandos = data?.comandos || [];
      this.dom.modalComandosLista.innerHTML = comandos
        .map((c) => {
          const esDetener = Number(c.codigo) === 9;
          return `
          <label class="d-flex justify-content-between align-items-center p-2 rounded bg-black bg-opacity-25 border border-secondary-subtle">
            <div>
              <span class="badge ${c.activo ? "bg-success" : "bg-secondary"} me-2">#${c.codigo}</span>
              <strong class="text-white small">${escapeHtml(c.nombre)}</strong>
              <small class="text-secondary d-block ms-4">${escapeHtml(c.descripcion || "")}</small>
            </div>
            <div class="form-check form-switch m-0">
              <input class="form-check-input check-comando-unidad" type="checkbox" value="${c.codigo}" ${c.activo || esDetener ? "checked" : ""} ${esDetener ? "disabled" : ""}>
            </div>
          </label>`;
        })
        .join("");
    } catch (err) {
      this.dom.modalComandosLista.innerHTML = `<div class="alert alert-danger py-2 small mb-0">Error al cargar comandos: ${escapeHtml(err.message)}</div>`;
    }
  }

  _renderTablaClientes() {
    if (!this.dom.tbodyClientes) return;
    this.dom.tbodyClientes.innerHTML = this.clientesCache
      .map(
        (c) => `
      <tr>
        <td>#${c.id_usuario}</td>
        <td class="text-white fw-semibold">${escapeHtml(c.nombre_completo)}</td>
        <td><small>${escapeHtml(c.correo)}</small></td>
        <td><span class="badge ${c.rol_codigo === "ADMIN" ? "bg-danger" : c.rol_codigo === "USUARIO" ? "bg-primary" : "bg-info text-dark"}">${escapeHtml(c.rol_codigo)}</span></td>
        <td><span class="badge bg-secondary">${c.total_unidades || 0}</span></td>
        <td>${c.activo ? '<span class="badge bg-success">Activo</span>' : '<span class="badge bg-secondary">Inactivo</span>'}</td>
      </tr>`
      )
      .join("");
  }

  _renderTablaAuditoria(rows) {
    if (!this.dom.tbodyAuditoria) return;
    if (!rows.length) {
      this.dom.tbodyAuditoria.innerHTML = `<tr><td colspan="6" class="text-center text-secondary py-3">Sin registros de auditoría</td></tr>`;
      return;
    }
    this.dom.tbodyAuditoria.innerHTML = rows
      .map((a) => {
        const { fecha, hora } = formatearFechaHora(a.fecha_hora);
        const resClass = a.resultado === "EXITO" ? "bg-success" : "bg-danger";
        return `
        <tr>
          <td><small class="text-secondary">${fecha} ${hora}</small></td>
          <td><small class="text-white">${escapeHtml(a.actor_correo || "Sistema")}</small> <span class="badge bg-dark border border-secondary">${escapeHtml(a.actor_rol || "-")}</span></td>
          <td><code class="text-info">${escapeHtml(a.accion)}</code></td>
          <td><small>${escapeHtml(a.recurso)}</small></td>
          <td><span class="badge ${resClass}">${escapeHtml(a.resultado)}</span></td>
          <td><small class="text-secondary">${escapeHtml(a.detalle || "")}</small></td>
        </tr>`;
      })
      .join("");
  }

  // =========================================================================
  // USUARIO COMPRADOR: MIS VEHÍCULOS + SOPORTE TÉCNICO
  // =========================================================================
  async cargarMisVehiculos(activeVehicleId) {
    try {
      const unidades = await apiService.getMisVehiculos();
      this.unidadesCache = unidades || [];

      if (this.dom.editorSelectVehiculo) {
        this.dom.editorSelectVehiculo.innerHTML = this.unidadesCache
          .map((u) => `<option value="${u.id_vehiculo}">#${u.id_vehiculo} · ${escapeHtml(u.nombre)}</option>`)
          .join("");
      }

      if (!this.dom.misVehiculosGrid) return this.unidadesCache;
      if (!this.unidadesCache.length) {
        this.dom.misVehiculosGrid.innerHTML = `<div class="col-12"><div class="alert alert-secondary">Aún no tienes vehículos asignados a tu cuenta. Solicita al Administrador la asignación de tu unidad.</div></div>`;
        return [];
      }

      this.dom.misVehiculosGrid.innerHTML = this.unidadesCache
        .map((u) => {
          const esActiva = Number(activeVehicleId) === Number(u.id_vehiculo);
          return `
          <div class="col-12 col-md-6">
            <div class="glass-card p-3 h-100 ${esActiva ? "border-info" : ""}">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                  <span class="badge bg-primary mb-1">Unidad #${u.id_vehiculo} · ${escapeHtml(u.numero_serie || "ESP32")}</span>
                  <h4 class="h6 text-white fw-bold mb-0">${escapeHtml(u.nombre)}</h4>
                  <small class="text-secondary">${escapeHtml(u.modelo_comercial_nombre || u.modelo)}</small>
                </div>
                <span class="badge bg-success">${escapeHtml(u.estado_comercial)}</span>
              </div>
              <p class="small text-secondary mb-2">${escapeHtml(u.descripcion || "Unidad IoT lista para operación")}</p>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input switch-soporte-unidad" type="checkbox" id="soporte_${u.id_vehiculo}" data-id="${u.id_vehiculo}" ${u.soporte_autorizado ? "checked" : ""}>
                <label class="form-check-label small text-secondary" for="soporte_${u.id_vehiculo}">
                  Autorizar soporte técnico remoto al Administrador
                </label>
              </div>
              <button class="btn btn-sm ${esActiva ? "btn-info" : "btn-outline-info"} w-100 btn-seleccionar-mi-unidad" data-id="${u.id_vehiculo}" data-nombre="${escapeHtml(u.nombre)}">
                <i class="bi bi-controller me-1"></i> ${esActiva ? "Unidad Activa (Ir a Control)" : "Operar y Monitorear esta Unidad"}
              </button>
            </div>
          </div>`;
        })
        .join("");

      this.dom.misVehiculosGrid.querySelectorAll(".btn-seleccionar-mi-unidad").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (this.onSelectVehicle) this.onSelectVehicle(Number(btn.dataset.id), btn.dataset.nombre, true);
        });
      });

      this.dom.misVehiculosGrid.querySelectorAll(".switch-soporte-unidad").forEach((chk) => {
        chk.addEventListener("change", async () => {
          const id = Number(chk.dataset.id);
          try {
            const res = await apiService.autorizarSoporte(id, chk.checked);
            this.showFeedback(res.mensaje, "info");
          } catch (err) {
            chk.checked = !chk.checked;
            this.showFeedback(`Error: ${err.message}`, "danger");
          }
        });
      });

      return this.unidadesCache;
    } catch (err) {
      this.showFeedback(`Error cargando Mis Vehículos: ${err.message}`, "danger");
      return [];
    }
  }

  // =========================================================================
  // EDITOR VISUAL DE DEMOS (FÁBRICA Y PRIVADAS)
  // =========================================================================
  async cargarEditorDemosVehiculo(idVehiculo) {
    if (!idVehiculo) return;
    this.editorVehiculoId = Number(idVehiculo);
    if (this.dom.editorSelectVehiculo) this.dom.editorSelectVehiculo.value = String(idVehiculo);

    try {
      const [comandos, demos] = await Promise.all([
        apiService.getComandos(idVehiculo),
        apiService.getDemosEditor(idVehiculo),
      ]);
      this.editorComandos = (comandos || []).filter((c) => c.activo);

      if (this.dom.editorSelectComando) {
        this.dom.editorSelectComando.innerHTML = this.editorComandos
          .map((c) => `<option value="${c.id_comando}">#${c.codigo} · ${escapeHtml(c.nombre)}</option>`)
          .join("");
      }

      if (this.dom.editorListaDemos) {
        if (!demos || !demos.length) {
          this.dom.editorListaDemos.innerHTML = `<div class="text-secondary small">No hay demos registradas para esta unidad.</div>`;
        } else {
          this.dom.editorListaDemos.innerHTML = demos
            .map(
              (d) => `
            <div class="d-flex justify-content-between align-items-center p-2 mb-2 rounded bg-dark border border-secondary-subtle">
              <div>
                <span class="badge ${d.tipo_demo === "FABRICA" ? "bg-warning text-dark" : "bg-primary"} me-1">${escapeHtml(d.tipo_demo || "FABRICA")}</span>
                <strong class="text-white small">${escapeHtml(d.nombre)}</strong>
                <div class="text-secondary" style="font-size:0.75rem">${(d.pasos || []).length} pasos · ${(Number(d.duracion_total_ms || 0) / 1000).toFixed(1)}s</div>
              </div>
              <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-info btn-cargar-demo-ed" data-id="${d.id_demo}" title="Editar pasos"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger btn-del-demo-ed" data-id="${d.id_demo}" title="Eliminar"><i class="bi bi-trash"></i></button>
              </div>
            </div>`
            )
            .join("");

          this.dom.editorListaDemos.querySelectorAll(".btn-cargar-demo-ed").forEach((btn) => {
            btn.addEventListener("click", () => {
              const found = demos.find((x) => x.id_demo === Number(btn.dataset.id));
              if (!found) return;
              this.editorDemoId = found.id_demo;
              if (this.dom.editorNombre) this.dom.editorNombre.value = found.nombre;
              if (this.dom.editorDescripcion) this.dom.editorDescripcion.value = found.descripcion || "";
              this.editorPasos = (found.pasos || []).map((p) => ({
                id_comando: p.id_comando,
                comando: p.comando,
                codigo: p.codigo,
                duracion_ms: p.duracion_ms,
                pausa_ms: p.pausa_ms,
              }));
              this._renderEditorPasos();
            });
          });

          this.dom.editorListaDemos.querySelectorAll(".btn-del-demo-ed").forEach((btn) => {
            btn.addEventListener("click", async () => {
              if (!confirm("¿Eliminar esta secuencia DEMO?")) return;
              try {
                await apiService.eliminarDemoEditor(Number(btn.dataset.id));
                this.showFeedback("DEMO eliminada.", "info");
                await this.cargarEditorDemosVehiculo(this.editorVehiculoId);
                if (this.onDemosChanged) this.onDemosChanged(this.editorVehiculoId);
              } catch (err) {
                this.showFeedback(`No permitido: ${err.message}`, "danger");
              }
            });
          });
        }
      }
    } catch (err) {
      this.showFeedback(`Error cargando editor de demos: ${err.message}`, "danger");
    }
  }

  _renderEditorPasos() {
    if (!this.dom.editorPasosBody) return;
    if (!this.editorPasos.length) {
      this.dom.editorPasosBody.innerHTML = `<tr><td colspan="5" class="text-center text-secondary py-2">Agrega pasos para construir la secuencia</td></tr>`;
      if (this.dom.editorDuracionTotal) this.dom.editorDuracionTotal.textContent = "0.0 s";
      return;
    }

    const totalMs = this.editorPasos.reduce((acc, p) => acc + Number(p.duracion_ms) + Number(p.pausa_ms), 0);
    if (this.dom.editorDuracionTotal) this.dom.editorDuracionTotal.textContent = `${(totalMs / 1000).toFixed(1)} s`;

    this.dom.editorPasosBody.innerHTML = this.editorPasos
      .map(
        (p, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><span class="badge bg-primary">#${p.codigo} ${escapeHtml(p.comando)}</span></td>
        <td>${p.duracion_ms} ms</td>
        <td>${p.pausa_ms} ms</td>
        <td>
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-secondary btn-paso-up" data-idx="${i}" ${i === 0 ? "disabled" : ""}><i class="bi bi-arrow-up"></i></button>
            <button class="btn btn-outline-secondary btn-paso-down" data-idx="${i}" ${i === this.editorPasos.length - 1 ? "disabled" : ""}><i class="bi bi-arrow-down"></i></button>
            <button class="btn btn-outline-danger btn-paso-del" data-idx="${i}"><i class="bi bi-x"></i></button>
          </div>
        </td>
      </tr>`
      )
      .join("");

    this.dom.editorPasosBody.querySelectorAll(".btn-paso-up").forEach((b) =>
      b.addEventListener("click", () => {
        const idx = Number(b.dataset.idx);
        [this.editorPasos[idx - 1], this.editorPasos[idx]] = [this.editorPasos[idx], this.editorPasos[idx - 1]];
        this._renderEditorPasos();
      })
    );
    this.dom.editorPasosBody.querySelectorAll(".btn-paso-down").forEach((b) =>
      b.addEventListener("click", () => {
        const idx = Number(b.dataset.idx);
        [this.editorPasos[idx + 1], this.editorPasos[idx]] = [this.editorPasos[idx], this.editorPasos[idx + 1]];
        this._renderEditorPasos();
      })
    );
    this.dom.editorPasosBody.querySelectorAll(".btn-paso-del").forEach((b) =>
      b.addEventListener("click", () => {
        this.editorPasos.splice(Number(b.dataset.idx), 1);
        this._renderEditorPasos();
      })
    );
  }

  // =========================================================================
  // INVITADO: CATÁLOGO PÚBLICO Y RESERVA EXCLUSIVA DE EXHIBICIÓN
  // =========================================================================
  async cargarCatalogoPublico() {
    try {
      const cat = await apiService.getCatalogoPublico();
      const modelos = cat?.modelos || [];
      const exhibicion = cat?.unidades_exhibicion || [];

      if (this.dom.catalogoModelosGrid) {
        this.dom.catalogoModelosGrid.innerHTML = modelos
          .map(
            (m) => `
          <div class="col-12 col-md-6">
            <div class="glass-card p-3 h-100">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="badge bg-info-subtle text-info">${escapeHtml(m.categoria)}</span>
                <strong class="text-success">$${Number(m.precio_referencia || 0).toLocaleString("es-MX")} MXN</strong>
              </div>
              <h4 class="h6 text-white fw-bold"><i class="bi ${escapeHtml(m.imagen_icono || "bi-truck-front")} me-1 text-info"></i>${escapeHtml(m.nombre)}</h4>
              <p class="small text-secondary mb-2">${escapeHtml(m.descripcion || "")}</p>
              <small class="text-secondary">Comandos del modelo: <code>${escapeHtml(m.comandos_soportados)}</code></small>
            </div>
          </div>`
          )
          .join("");
      }

      if (this.dom.catalogoExhibicionGrid) {
        if (!exhibicion.length) {
          this.dom.catalogoExhibicionGrid.innerHTML = `<div class="col-12"><div class="alert alert-secondary">No hay unidades en exhibición disponibles en este momento.</div></div>`;
          return;
        }
        this.dom.catalogoExhibicionGrid.innerHTML = exhibicion
          .map(
            (u) => `
          <div class="col-12 col-md-6">
            <div class="monitoreo-card-destacada p-3 h-100">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                  <span class="badge bg-info text-dark mb-1">EXHIBICIÓN · Unidad #${u.id_vehiculo}</span>
                  <h4 class="h6 text-white fw-bold mb-0">${escapeHtml(u.nombre)}</h4>
                  <small class="text-secondary">${escapeHtml(u.modelo_comercial)} (${escapeHtml(u.microcontrolador)})</small>
                </div>
                ${
                  u.disponible
                    ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Libre</span>'
                    : `<span class="badge bg-danger"><i class="bi bi-hourglass-split me-1"></i>Ocupada (${u.segundos_restantes}s)</span>`
                }
              </div>
              <p class="small text-secondary mb-2">Comandos permitidos en prueba: <code>Avanzar, Retroceder, Izquierda, Derecha, Luz, DETENER</code></p>
              <button class="btn btn-info btn-control-touch w-100 btn-reservar-invitado" data-id="${u.id_vehiculo}" data-nombre="${escapeHtml(u.nombre)}" ${u.disponible ? "" : "disabled"}>
                <i class="bi bi-stopwatch me-1"></i> ${u.disponible ? "Reservar Prueba Exclusiva (90s)" : `Ocupada por ${escapeHtml(u.ocupado_por || "otro visitante")}`}
              </button>
            </div>
          </div>`
          )
          .join("");

        this.dom.catalogoExhibicionGrid.querySelectorAll(".btn-reservar-invitado").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const nombreInv = this.dom.inputNombreInvitado?.value.trim() || "Visitante Exhibición";
            const idVeh = Number(btn.dataset.id);
            try {
              const res = await apiService.iniciarSesionInvitado(idVeh, nombreInv, 90);
              this.showFeedback(`Reserva exclusiva otorgada por ${res.sesion.duracion_segundos}s en ${res.sesion.nombre_vehiculo}.`, "success");
              if (this.onGuestSessionStarted) this.onGuestSessionStarted(res.sesion);
            } catch (err) {
              this.showFeedback(`No se pudo reservar: ${err.message}`, "danger");
              await this.cargarCatalogoPublico();
            }
          });
        });
      }
    } catch (err) {
      this.showFeedback(`Error al cargar catálogo público: ${err.message}`, "danger");
    }
  }
}

export const administracionManager = new AdministracionManager();
