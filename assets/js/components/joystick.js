/**
 * joystick.js - Control táctil y de mouse Pointer Events para navegación
 */

export class VirtualJoystick {
  constructor(containerEl, onDirectionChange) {
    this.container = containerEl;
    this.stick = containerEl.querySelector(".joystick-stick");
    this.onDirectionChange = onDirectionChange;

    this.active = false;
    this.pointerId = null;
    this.currentDirection = "NEUTRAL"; // NEUTRAL, AVANZAR, RETROCEDER, IZQUIERDA, DERECHA

    this.centerX = 0;
    this.centerY = 0;
    this.maxRadius = 55; // Píxeles máximos de desplazamiento
    this.deadZone = 18;  // Zona muerta central

    this._bindEvents();
  }

  _bindEvents() {
    this.container.addEventListener("pointerdown", this._onPointerDown.bind(this));
    window.addEventListener("pointermove", this._onPointerMove.bind(this));
    window.addEventListener("pointerup", this._onPointerUp.bind(this));
    window.addEventListener("pointercancel", this._onPointerUp.bind(this));
  }

  _updateCenter() {
    const rect = this.container.getBoundingClientRect();
    this.centerX = rect.left + rect.width / 2;
    this.centerY = rect.top + rect.height / 2;
  }

  _onPointerDown(e) {
    if (this.active) return;
    this.active = true;
    this.pointerId = e.pointerId;
    this.container.setPointerCapture(e.pointerId);
    this._updateCenter();
    this._processCoord(e.clientX, e.clientY);
  }

  _onPointerMove(e) {
    if (!this.active || e.pointerId !== this.pointerId) return;
    this._processCoord(e.clientX, e.clientY);
  }

  _onPointerUp(e) {
    if (!this.active || e.pointerId !== this.pointerId) return;
    this.active = false;
    this.pointerId = null;
    this._resetStick();
    if (this.currentDirection !== "NEUTRAL") {
      this.currentDirection = "NEUTRAL";
      this.onDirectionChange("NEUTRAL");
    }
  }

  _processCoord(clientX, clientY) {
    const dx = clientX - this.centerX;
    const dy = clientY - this.centerY;
    const distance = Math.hypot(dx, dy);

    let stickX = dx;
    let stickY = dy;

    if (distance > this.maxRadius) {
      const angle = Math.atan2(dy, dx);
      stickX = Math.cos(angle) * this.maxRadius;
      stickY = Math.sin(angle) * this.maxRadius;
    }

    this.stick.style.transform = `translate(${stickX}px, ${stickY}px)`;

    // Detección de dirección
    let newDirection = "NEUTRAL";
    if (distance > this.deadZone) {
      const absX = Math.abs(dx);
      const absY = Math.abs(dy);

      if (absY >= absX) {
        newDirection = dy < 0 ? "AVANZAR" : "RETROCEDER";
      } else {
        newDirection = dx < 0 ? "IZQUIERDA" : "DERECHA";
      }
    }

    if (newDirection !== this.currentDirection) {
      this.currentDirection = newDirection;
      this.onDirectionChange(newDirection);
    }
  }

  _resetStick() {
    this.stick.style.transform = "translate(0px, 0px)";
  }
}

