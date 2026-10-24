import * as THREE from "three";
import { SceneManager } from "../scene/SceneManager";

export class ScalePicker {
  private sceneManager: SceneManager;
  private isActive: boolean = false;
  private p1: THREE.Vector3 | null = null;
  private p2: THREE.Vector3 | null = null;
  private marker1: THREE.Mesh | null = null;
  private marker2: THREE.Mesh | null = null;
  private line: THREE.Line | null = null;
  private panel: HTMLElement | null = null;
  private realDistanceM: number = 1.0;

  constructor(sceneManager: SceneManager) {
    this.sceneManager = sceneManager;
    this.createUI();
    this.bindEvents();
  }

  private createUI(): void {
    let panel = document.getElementById("scale-panel");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "scale-panel";
      panel.style.position = "absolute";
      panel.style.bottom = "20px";
      panel.style.right = "20px";
      panel.style.width = "340px";
      panel.style.background = "rgba(15, 23, 42, 0.88)";
      panel.style.border = "1px solid rgba(0, 240, 255, 0.3)";
      panel.style.borderRadius = "10px";
      panel.style.padding = "16px";
      panel.style.backdropFilter = "blur(14px)";
      panel.style.boxShadow = "0 8px 32px rgba(0, 0, 0, 0.5)";
      panel.style.fontFamily = "'JetBrains Mono', monospace";
      panel.style.fontSize = "12px";
      panel.style.color = "#f8fafc";
      panel.style.zIndex = "25";
      panel.style.display = "none";
      document.body.appendChild(panel);
    }
    this.panel = panel;
    this.updateUI();
  }

  private bindEvents(): void {
    window.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "p" || e.key === "P") {
        this.toggle();
      }
    });

    const canvas = this.sceneManager.getCanvas();
    canvas.addEventListener("click", () => {
      if (!this.isActive) return;
      this.pickPoint();
    });
  }

  public toggle(): void {
    this.isActive = !this.isActive;
    if (this.panel) {
      this.panel.style.display = this.isActive ? "block" : "none";
    }
    if (!this.isActive) {
      this.clearMarkers();
    } else {
      this.updateUI();
    }
  }

  private pickPoint(): void {
    const camera = this.sceneManager.getCamera();
    const raycaster = new THREE.Raycaster();
    // Cast ray forward from center of view
    raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);

    // Intersect against floor plane Y = 0 as reference plane
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    const target = new THREE.Vector3();
    const hit = raycaster.ray.intersectPlane(plane, target);

    const hitPoint = hit || raycaster.ray.at(2.5, new THREE.Vector3());

    if (!this.p1 || (this.p1 && this.p2)) {
      this.clearMarkers();
      this.p1 = hitPoint.clone();
      this.p2 = null;
      this.marker1 = this.createMarker(this.p1, 0x00f0ff);
    } else if (this.p1 && !this.p2) {
      this.p2 = hitPoint.clone();
      this.marker2 = this.createMarker(this.p2, 0x3b82f6);
      this.createConnectorLine(this.p1, this.p2);
    }
    this.updateUI();
  }

  private createMarker(pos: THREE.Vector3, color: number): THREE.Mesh {
    const geom = new THREE.SphereGeometry(0.04, 16, 16);
    const mat = new THREE.MeshBasicMaterial({ color, wireframe: false });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.copy(pos);
    this.sceneManager.getScene().add(mesh);
    return mesh;
  }

  private createConnectorLine(p1: THREE.Vector3, p2: THREE.Vector3): void {
    const geom = new THREE.BufferGeometry().setFromPoints([p1, p2]);
    const mat = new THREE.LineBasicMaterial({ color: 0x00f0ff, linewidth: 2 });
    this.line = new THREE.Line(geom, mat);
    this.sceneManager.getScene().add(this.line);
  }

  private clearMarkers(): void {
    const scene = this.sceneManager.getScene();
    if (this.marker1) {
      scene.remove(this.marker1);
      this.marker1 = null;
    }
    if (this.marker2) {
      scene.remove(this.marker2);
      this.marker2 = null;
    }
    if (this.line) {
      scene.remove(this.line);
      this.line = null;
    }
    this.p1 = null;
    this.p2 = null;
    this.updateUI();
  }

  private updateUI(): void {
    if (!this.panel) return;

    let distSfm = 0;
    let scaleFactor = 1.0;
    let cliFlag = "--scale-points ... --scale-distance 1.00";

    if (this.p1 && this.p2) {
      distSfm = this.p1.distanceTo(this.p2);
      if (distSfm > 1e-4) {
        scaleFactor = this.realDistanceM / distSfm;
        const ptsStr = `${this.p1.x.toFixed(3)},${this.p1.y.toFixed(3)},${this.p1.z.toFixed(3)},${this.p2.x.toFixed(3)},${this.p2.y.toFixed(3)},${this.p2.z.toFixed(3)}`;
        cliFlag = `--scale-points "${ptsStr}" --scale-distance ${this.realDistanceM.toFixed(2)}`;
      }
    }

    const p1Str = this.p1 ? `[${this.p1.x.toFixed(3)}, ${this.p1.y.toFixed(3)}, ${this.p1.z.toFixed(3)}]` : "Click crosshair for Point 1";
    const p2Str = this.p2 ? `[${this.p2.x.toFixed(3)}, ${this.p2.y.toFixed(3)}, ${this.p2.z.toFixed(3)}]` : (this.p1 ? "Click crosshair for Point 2" : "--");

    this.panel.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <span style="color: #00f0ff; font-weight: 700;">SCALE CALIBRATION</span>
        <button id="scale-close-btn" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 14px;">✕</button>
      </div>
      <div style="color: #94a3b8; font-size: 11px; margin-bottom: 8px;">
        Aim crosshair at two points on a known object (e.g. 1m floor tape) and click.
      </div>
      <div style="margin-bottom: 4px;">P1: <span style="color: #00f0ff;">${p1Str}</span></div>
      <div style="margin-bottom: 8px;">P2: <span style="color: #3b82f6;">${p2Str}</span></div>
      ${this.p1 && this.p2 ? `
        <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; margin-top: 8px;">
          <div>SfM Distance: <span style="color: #fff; font-weight: 600;">${distSfm.toFixed(3)} units</span></div>
          <div style="margin: 6px 0; display: flex; align-items: center; gap: 8px;">
            <span>Real (m):</span>
            <input id="scale-real-input" type="number" step="0.05" value="${this.realDistanceM}" style="width: 70px; background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 2px 6px; border-radius: 4px; font-family: inherit; font-size: 12px;" />
          </div>
          <div>Scale Factor: <span style="color: #22c55e; font-weight: 600;">${scaleFactor.toFixed(4)}x</span></div>
          <div style="margin-top: 10px;">
            <button id="scale-copy-btn" style="width: 100%; background: #00f0ff; color: #08090c; border: none; font-weight: 700; padding: 6px; border-radius: 4px; cursor: pointer; font-size: 11px;">
              COPY CLI ARGUMENTS
            </button>
          </div>
        </div>
      ` : ""}
      <div style="margin-top: 8px; display: flex; justify-content: flex-end;">
        <button id="scale-clear-btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #94a3b8; padding: 3px 8px; border-radius: 4px; cursor: pointer; font-size: 10px;">
          Reset Points
        </button>
      </div>
    `;

    const closeBtn = document.getElementById("scale-close-btn");
    if (closeBtn) closeBtn.onclick = () => this.toggle();

    const clearBtn = document.getElementById("scale-clear-btn");
    if (clearBtn) clearBtn.onclick = () => this.clearMarkers();

    const realInput = document.getElementById("scale-real-input") as HTMLInputElement;
    if (realInput) {
      realInput.onchange = () => {
        const val = parseFloat(realInput.value);
        if (val > 0) {
          this.realDistanceM = val;
          this.updateUI();
        }
      };
    }

    const copyBtn = document.getElementById("scale-copy-btn");
    if (copyBtn) {
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(cliFlag).then(() => {
          copyBtn.textContent = "COPIED TO CLIPBOARD!";
          setTimeout(() => {
            if (copyBtn) copyBtn.textContent = "COPY CLI ARGUMENTS";
          }, 2000);
        });
      };
    }
  }
}
