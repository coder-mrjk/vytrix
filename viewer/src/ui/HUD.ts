import { eventBus } from "../utils/eventBus";

export class HUD {
  private fpsEl: HTMLElement | null = null;
  private frameTimeEl: HTMLElement | null = null;
  private posEl: HTMLElement | null = null;
  private modeEl: HTMLElement | null = null;
  private splatsEl: HTMLElement | null = null;

  private frameCount: number = 0;
  private lastTime: number = performance.now();
  private fps: number = 60;
  private frameTime: number = 16.6;

  constructor() {
    this.fpsEl = document.getElementById("hud-fps");
    this.frameTimeEl = document.getElementById("hud-frame-time");
    this.posEl = document.getElementById("hud-pos");
    this.modeEl = document.getElementById("hud-mode");
    this.splatsEl = document.getElementById("hud-splats");

    this.bindEvents();
  }

  private bindEvents(): void {
    eventBus.on("telemetry:update", (data: any) => {
      if (this.posEl && data.position) {
        this.posEl.textContent = `[${data.position[0]}, ${data.position[1]}, ${data.position[2]}]`;
      }
      if (this.modeEl && data.mode) {
        this.modeEl.textContent = data.mode;
      }
    });

    eventBus.on("splats:loaded", (count: any) => {
      if (this.splatsEl) {
        this.splatsEl.textContent = Number(count).toLocaleString();
      }
    });
  }

  public update(now: number): void {
    this.frameCount++;
    const delta = now - this.lastTime;

    if (delta >= 500) { // Update FPS every 500ms
      this.fps = Math.round((this.frameCount * 1000) / delta);
      this.frameTime = parseFloat((delta / this.frameCount).toFixed(1));

      if (this.fpsEl) this.fpsEl.textContent = `${this.fps}`;
      if (this.frameTimeEl) this.frameTimeEl.textContent = `${this.frameTime}`;

      this.frameCount = 0;
      this.lastTime = now;
    }
  }
}
