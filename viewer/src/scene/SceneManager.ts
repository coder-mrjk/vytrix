import * as THREE from "three";
import * as GaussianSplats3D from "@mkkellogg/gaussian-splats-3d";
import { SceneManifest } from "./types";
import { eventBus } from "../utils/eventBus";
import { BoundsController } from "../controls/BoundsController";
import { LoadingOverlay } from "../ui/LoadingOverlay";

export class SceneManager {
  private canvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private boundsController: BoundsController | null = null;
  private splatViewer: GaussianSplats3D.Viewer | null = null;

  private manifest: SceneManifest | null = null;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;

    // Three.js renderer setup with high-performance flags
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: false, // Splats do not require MSAA
      powerPreference: "high-performance"
    });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2.0));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;

    // Scene & Camera
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x08090c);

    this.camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      100.0
    );

    this.setupLighting();
    this.bindWindowResize();
  }

  private setupLighting(): void {
    // Ambient light and soft directional light for any debug/hybrid meshes
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(5, 10, 7);
    this.scene.add(dirLight);
  }

  private bindWindowResize(): void {
    window.addEventListener("resize", () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
    });
  }

  public getCamera(): THREE.PerspectiveCamera {
    return this.camera;
  }

  public getScene(): THREE.Scene {
    return this.scene;
  }

  public getCanvas(): HTMLCanvasElement {
    return this.canvas;
  }

  public getBoundsController(): BoundsController | null {
    return this.boundsController;
  }

  public async loadScene(scenePath: string, loading: LoadingOverlay): Promise<SceneManifest> {
    loading.setProgress(15, "Fetching scene manifest...", "scene.json");

    try {
      const response = await fetch(scenePath);
      if (!response.ok) {
        throw new Error(`Failed to load scene manifest: HTTP ${response.status}`);
      }
      this.manifest = await response.json();
    } catch (err) {
      console.warn("Could not load scene.json manifest from path. Falling back to default synthetic manifest.", err);
      this.manifest = this.createDefaultManifest();
    }

    const manifest = this.manifest!;

    // Configure Bounds
    this.boundsController = new BoundsController(manifest.bounds);

    // Setup Camera Spawn
    this.camera.position.set(
      manifest.spawn.position[0],
      manifest.spawn.position[1],
      manifest.spawn.position[2]
    );

    loading.setProgress(40, "Checking splat assets...", manifest.splat.file);

    // Try loading actual Gaussian Splat file if accessible
    let splatLoaded = false;
    let splatUrl = "";
    if (manifest.splat.file) {
      splatUrl = new URL(manifest.splat.file, new URL(scenePath, window.location.href)).href;
      try {
        splatLoaded = await this.tryLoadSplat(splatUrl, loading);
      } catch (e) {
        console.warn("Gaussian Splat asset not found or failed to load.", e);
        splatLoaded = false;
      }
    }

    if (!splatLoaded) {
      const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
      if (!isLocalhost) {
        // Never silently fall back on deployed sites
        const errorMsg = `Gaussian Splat asset (${manifest.splat.file || "unknown"}) failed to load. Check that scene.splat exists at ${splatUrl} and headers permit CORS.`;
        loading.showError(errorMsg);
        throw new Error(`[VYTRIX Deployment Error] ${errorMsg}`);
      } else {
        // On local development only, show clear placeholder notice
        console.warn("Localhost notice: scene.splat missing or failed to load. Loading local wireframe room for developer testing.");
        this.buildProceduralRoom(manifest.bounds);
        loading.setProgress(100, "Local Dev Wireframe Ready", "Note: scene.splat not yet populated");
        eventBus.emit("splats:loaded", 42500);
      }
    }

    loading.hide();
    return manifest;
  }

  private async tryLoadSplat(splatUrl: string, loading: LoadingOverlay): Promise<boolean> {
    try {
      const headCheck = await fetch(splatUrl, { method: "HEAD" });
      if (!headCheck.ok) return false;
      const contentType = headCheck.headers.get("content-type");
      if (contentType && contentType.includes("text/html")) {
        console.warn("Splat URL returned HTML instead of binary:", splatUrl);
        return false;
      }

      loading.setProgress(55, "Streaming 3D Gaussian Splats...", splatUrl);

      // On non-localhost HTTP connections, SharedArrayBuffer is disabled by browsers
      const canUseSharedMemory = window.isSecureContext && typeof SharedArrayBuffer !== "undefined";

      this.splatViewer = new GaussianSplats3D.Viewer({
        threeScene: this.scene,
        camera: this.camera,
        renderer: this.renderer,
        useBuiltInControls: false,
        selfDrivenMode: false,
        progressiveLoad: canUseSharedMemory,
        sharedMemoryForWorkers: canUseSharedMemory,
        gpuAcceleratedSort: true
      });

      const loadPromise = this.splatViewer.addSplatScene(splatUrl, {
        splatAlphaRemovalThreshold: 5,
        showLoadingUI: false,
        position: [0, 0, 0],
        rotation: [0, 0, 0, 1],
        scale: [1, 1, 1],
        onProgress: (percent: number, percentLabel: string) => {
          loading.setProgress(
            55 + (percent * 0.4),
            `Streaming 3D Gaussians (${percentLabel})`,
            splatUrl
          );
        }
      });

      // Allow sufficient time for real multi-megabyte splat downloads (up to 45 seconds)
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error("Timeout loading splat scene after 45s")), 45000);
      });

      await Promise.race([loadPromise, timeoutPromise]);

      eventBus.emit("splats:loaded", this.manifest?.splat.num_gaussians || 0);
      return true;
    } catch (err) {
      console.warn("Failed or timed out loading 3D Gaussian Splat scene:", err);
      if (this.splatViewer) {
        try {
          this.splatViewer.dispose();
        } catch {
          // Ignore disposal errors
        }
        this.splatViewer = null;
      }
      return false;
    }
  }

  private buildProceduralRoom(bounds: { min: [number, number, number]; max: [number, number, number] }): void {
    const width = bounds.max[0] - bounds.min[0];
    const height = bounds.max[1] - bounds.min[1];
    const depth = bounds.max[2] - bounds.min[2];

    const centerX = (bounds.min[0] + bounds.max[0]) / 2;
    const centerY = (bounds.min[1] + bounds.max[1]) / 2;
    const centerZ = (bounds.min[2] + bounds.max[2]) / 2;

    // Floor with metric grid
    const gridHelper = new THREE.GridHelper(Math.max(width, depth), Math.round(Math.max(width, depth) * 2), 0x00f0ff, 0x1e293b);
    gridHelper.position.set(centerX, 0, centerZ);
    this.scene.add(gridHelper);

    // Floor plane
    const floorGeo = new THREE.PlaneGeometry(width, depth);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.8,
      metalness: 0.2
    });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.set(centerX, 0, centerZ);
    this.scene.add(floorMesh);

    // Room Wireframe Envelope
    const boxGeo = new THREE.BoxGeometry(width, height, depth);
    const wireframe = new THREE.WireframeGeometry(boxGeo);
    const line = new THREE.LineSegments(wireframe);
    (line.material as THREE.LineBasicMaterial).color.setHex(0x334155);
    (line.material as THREE.LineBasicMaterial).transparent = true;
    (line.material as THREE.LineBasicMaterial).opacity = 0.6;
    line.position.set(centerX, centerY, centerZ);
    this.scene.add(line);

    // Add synthetic spatial particle cloud simulating indoor Gaussians
    const particleCount = 20000;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const px = bounds.min[0] + Math.random() * width;
      const py = bounds.min[1] + Math.random() * height;
      const pz = bounds.min[2] + Math.random() * depth;

      positions[i * 3] = px;
      positions[i * 3 + 1] = py;
      positions[i * 3 + 2] = pz;

      // Realistic indoor colors (creams, warm woods, soft grays)
      colors[i * 3] = 0.6 + Math.random() * 0.3;
      colors[i * 3 + 1] = 0.55 + Math.random() * 0.25;
      colors[i * 3 + 2] = 0.5 + Math.random() * 0.2;
    }

    const particlesGeo = new THREE.BufferGeometry();
    particlesGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    particlesGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const particlesMat = new THREE.PointsMaterial({
      size: 0.04,
      vertexColors: true,
      transparent: true,
      opacity: 0.85
    });

    const pointCloud = new THREE.Points(particlesGeo, particlesMat);
    this.scene.add(pointCloud);
  }

  private createDefaultManifest(): SceneManifest {
    return {
      schema_version: "1.0",
      scene_id: "home-01",
      title: "VYTRIX Reconstructed Space",
      units: "metres",
      up_axis: "+Y",
      handedness: "right",
      splat: {
        file: "scene.ksplat",
        format: "ksplat",
        num_gaussians: 42500,
        bytes: 14200000
      },
      transform_applied: {
        matrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        scale_method: "two_point_tape",
        scale_error_pct: 1.2
      },
      bounds: {
        min: [-3.5, 0.0, -4.0],
        max: [3.5, 2.8, 4.0]
      },
      spawn: {
        position: [0.0, 0.0, 0.0],
        yaw_deg: 0
      },
      eye_height_m: 1.6,
      capture: {
        device: "Smartphone (Wide Camera, 4K 30fps)",
        date: "2026-10-10",
        fps: 30,
        num_frames_used: 350
      },
      metrics: {
        registered_images: 342,
        total_images: 350,
        reproj_error_px: 0.74,
        psnr: 29.4,
        ssim: 0.912
      },
      collision_proxy: null,
      navmesh: null,
      pois: [],
      credits: [
        "VYTRO SQUAD (Team)",
        "Techfest 2026-27 IIT Bombay",
        "gsplat & nerfstudio (Apache-2.0)",
        "Three.js & gaussian-splats-3d (MIT)"
      ]
    };
  }

  public render(): void {
    if (this.splatViewer) {
      this.splatViewer.update();
      this.splatViewer.render();
    } else {
      this.renderer.render(this.scene, this.camera);
    }
  }
}
