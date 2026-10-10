import * as THREE from "three";
import { BoundsController } from "./BoundsController";
import { eventBus } from "../utils/eventBus";

export class FirstPersonControls {
  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  private boundsController: BoundsController | null = null;

  // State
  private isLocked: boolean = false;
  private isFlyMode: boolean = false;
  private eyeHeight: number = 1.6;
  private spawnPosition: THREE.Vector3 = new THREE.Vector3(0, 1.6, 0);
  private spawnYaw: number = 0;

  // Euler angles for camera rotation
  private pitch: number = 0;
  private yaw: number = 0;

  // Movement dynamics
  private moveForward: boolean = false;
  private moveBackward: boolean = false;
  private moveLeft: boolean = false;
  private moveRight: boolean = false;
  private moveUp: boolean = false;
  private moveDown: boolean = false;
  private isRunning: boolean = false;

  private velocity: THREE.Vector3 = new THREE.Vector3();
  private walkSpeed: number = 1.6; // m/s
  private runMultiplier: number = 2.2;
  private mouseSensitivity: number = 0.0022;

  // Touch tracking for mobile devices
  private touchMoveId: number | null = null;
  private touchMoveStart: { x: number; y: number } = { x: 0, y: 0 };
  private touchLookId: number | null = null;
  private touchLookLast: { x: number; y: number } = { x: 0, y: 0 };
  private isTouchDevice: boolean = false;

  constructor(camera: THREE.PerspectiveCamera, domElement: HTMLElement) {
    this.camera = camera;
    this.domElement = domElement;

    this.bindEvents();
  }

  public setBoundsController(bounds: BoundsController): void {
    this.boundsController = bounds;
  }

  public setSpawn(position: [number, number, number], yawDeg: number, eyeHeight: number): void {
    this.eyeHeight = eyeHeight;
    this.spawnPosition.set(position[0], position[1] + eyeHeight, position[2]);
    this.spawnYaw = (yawDeg * Math.PI) / 180;
    this.resetPosition();
  }

  public resetPosition(): void {
    this.camera.position.copy(this.spawnPosition);
    this.yaw = this.spawnYaw;
    this.pitch = 0;
    this.velocity.set(0, 0, 0);
    this.updateCameraRotation();
    this.emitState();
  }

  public lock(): void {
    this.domElement.requestPointerLock();
  }

  public unlock(): void {
    document.exitPointerLock();
  }

  public getIsLocked(): boolean {
    return this.isLocked;
  }

  public toggleFlyMode(): void {
    this.isFlyMode = !this.isFlyMode;
    if (this.boundsController) {
      this.boundsController.setEnabled(!this.isFlyMode);
    }
    if (!this.isFlyMode) {
      // Snap back to eye height
      this.camera.position.y = this.eyeHeight;
    }
    this.emitState();
  }

  private bindEvents(): void {
    document.addEventListener("pointerlockchange", () => {
      this.isLocked = document.pointerLockElement === this.domElement;
      eventBus.emit("pointerlock:change", this.isLocked);
    });

    document.addEventListener("mousemove", (e: MouseEvent) => {
      if (!this.isLocked) return;

      this.yaw -= e.movementX * this.mouseSensitivity;
      this.pitch -= e.movementY * this.mouseSensitivity;

      // Clamp vertical pitch to prevent flipping (-85 deg to +85 deg)
      const maxPitch = (85 * Math.PI) / 180;
      this.pitch = Math.max(-maxPitch, Math.min(maxPitch, this.pitch));

      this.updateCameraRotation();
    });

    window.addEventListener("keydown", (e: KeyboardEvent) => {
      this.onKeyDown(e);
    });

    window.addEventListener("keyup", (e: KeyboardEvent) => {
      this.onKeyUp(e);
    });

    // Touch event support for smartphones and tablets
    window.addEventListener("touchstart", (e: TouchEvent) => {
      this.isTouchDevice = true;
      const width = window.innerWidth;
      for (let i = 0; i < e.changedTouches.length; i++) {
        const t = e.changedTouches[i];
        if (t.clientX < width / 2 && this.touchMoveId === null) {
          this.touchMoveId = t.identifier;
          this.touchMoveStart = { x: t.clientX, y: t.clientY };
        } else if (t.clientX >= width / 2 && this.touchLookId === null) {
          this.touchLookId = t.identifier;
          this.touchLookLast = { x: t.clientX, y: t.clientY };
        }
      }
    }, { passive: true });

    window.addEventListener("touchmove", (e: TouchEvent) => {
      const deadzone = 12;
      for (let i = 0; i < e.changedTouches.length; i++) {
        const t = e.changedTouches[i];
        if (t.identifier === this.touchMoveId) {
          const dx = t.clientX - this.touchMoveStart.x;
          const dy = t.clientY - this.touchMoveStart.y;
          this.moveForward = dy < -deadzone;
          this.moveBackward = dy > deadzone;
          this.moveRight = dx > deadzone;
          this.moveLeft = dx < -deadzone;
        } else if (t.identifier === this.touchLookId) {
          const dx = t.clientX - this.touchLookLast.x;
          const dy = t.clientY - this.touchLookLast.y;
          this.yaw -= dx * this.mouseSensitivity * 1.5;
          this.pitch -= dy * this.mouseSensitivity * 1.5;
          const maxPitch = (85 * Math.PI) / 180;
          this.pitch = Math.max(-maxPitch, Math.min(maxPitch, this.pitch));
          this.touchLookLast = { x: t.clientX, y: t.clientY };
          this.updateCameraRotation();
        }
      }
    }, { passive: true });

    const endTouch = (e: TouchEvent) => {
      for (let i = 0; i < e.changedTouches.length; i++) {
        const t = e.changedTouches[i];
        if (t.identifier === this.touchMoveId) {
          this.touchMoveId = null;
          this.moveForward = false;
          this.moveBackward = false;
          this.moveLeft = false;
          this.moveRight = false;
        } else if (t.identifier === this.touchLookId) {
          this.touchLookId = null;
        }
      }
    };

    window.addEventListener("touchend", endTouch);
    window.addEventListener("touchcancel", endTouch);
  }

  private onKeyDown(e: KeyboardEvent): void {
    switch (e.code) {
      case "KeyW":
      case "ArrowUp":
        this.moveForward = true;
        break;
      case "KeyS":
      case "ArrowDown":
        this.moveBackward = true;
        break;
      case "KeyA":
      case "ArrowLeft":
        this.moveLeft = true;
        break;
      case "KeyD":
      case "ArrowRight":
        this.moveRight = true;
        break;
      case "KeyE":
      case "Space":
        if (this.isFlyMode) this.moveUp = true;
        break;
      case "KeyQ":
      case "KeyC":
        if (this.isFlyMode) this.moveDown = true;
        break;
      case "ShiftLeft":
      case "ShiftRight":
        this.isRunning = true;
        break;
      case "KeyF":
        this.toggleFlyMode();
        break;
      case "KeyR":
        this.resetPosition();
        break;
    }
  }

  private onKeyUp(e: KeyboardEvent): void {
    switch (e.code) {
      case "KeyW":
      case "ArrowUp":
        this.moveForward = false;
        break;
      case "KeyS":
      case "ArrowDown":
        this.moveBackward = false;
        break;
      case "KeyA":
      case "ArrowLeft":
        this.moveLeft = false;
        break;
      case "KeyD":
      case "ArrowRight":
        this.moveRight = false;
        break;
      case "KeyE":
      case "Space":
        this.moveUp = false;
        break;
      case "KeyQ":
      case "KeyC":
        this.moveDown = false;
        break;
      case "ShiftLeft":
      case "ShiftRight":
        this.isRunning = false;
        break;
    }
  }

  private updateCameraRotation(): void {
    const euler = new THREE.Euler(0, 0, 0, "YXZ");
    euler.y = this.yaw;
    euler.x = this.pitch;
    this.camera.quaternion.setFromEuler(euler);
  }

  public update(deltaTime: number): void {
    if (!this.isLocked && !this.isTouchDevice) return;

    // Cap delta time to avoid large jumps if tab was blurred
    const dt = Math.min(deltaTime, 0.1);

    const speed = this.walkSpeed * (this.isRunning ? this.runMultiplier : 1.0);
    const damping = 10.0;

    // Movement direction vectors relative to camera yaw
    const forward = new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
    const right = new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw));

    const moveDir = new THREE.Vector3();
    if (this.moveForward) moveDir.add(forward);
    if (this.moveBackward) moveDir.sub(forward);
    if (this.moveRight) moveDir.add(right);
    if (this.moveLeft) moveDir.sub(right);

    if (moveDir.lengthSq() > 0) {
      moveDir.normalize();
    }

    // Target velocity
    const targetVelocity = moveDir.multiplyScalar(speed);
    if (this.isFlyMode) {
      if (this.moveUp) targetVelocity.y += speed;
      if (this.moveDown) targetVelocity.y -= speed;
    }

    // Smooth velocity damping
    this.velocity.x += (targetVelocity.x - this.velocity.x) * damping * dt;
    this.velocity.z += (targetVelocity.z - this.velocity.z) * damping * dt;
    if (this.isFlyMode) {
      this.velocity.y += (targetVelocity.y - this.velocity.y) * damping * dt;
    } else {
      this.velocity.y = 0;
    }

    // Integrate position
    this.camera.position.x += this.velocity.x * dt;
    this.camera.position.z += this.velocity.z * dt;

    if (this.isFlyMode) {
      this.camera.position.y += this.velocity.y * dt;
    } else {
      this.camera.position.y = this.eyeHeight;
    }

    // Clamp inside room envelope
    if (this.boundsController) {
      this.boundsController.clampPosition(this.camera.position);
    }

    this.emitState();
  }

  private emitState(): void {
    eventBus.emit("telemetry:update", {
      position: [
        parseFloat(this.camera.position.x.toFixed(2)),
        parseFloat(this.camera.position.y.toFixed(2)),
        parseFloat(this.camera.position.z.toFixed(2))
      ],
      mode: this.isFlyMode ? "FLY (FREE)" : `WALK (${this.eyeHeight.toFixed(1)}m)`,
      isLocked: this.isLocked
    });
  }
}
