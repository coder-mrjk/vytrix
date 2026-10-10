import { SceneManager } from "./scene/SceneManager";
import { FirstPersonControls } from "./controls/FirstPersonControls";
import { HUD } from "./ui/HUD";
import { LoadingOverlay } from "./ui/LoadingOverlay";
import { eventBus } from "./utils/eventBus";

async function init() {
  const canvas = document.getElementById("webgl-canvas") as HTMLCanvasElement;
  if (!canvas) {
    console.error("WebGL canvas element not found!");
    return;
  }

  const loading = new LoadingOverlay();
  const hud = new HUD();
  const sceneManager = new SceneManager(canvas);
  const controls = new FirstPersonControls(sceneManager.getCamera(), canvas);

  // Overlay Click-to-Explore
  const clickOverlay = document.getElementById("click-overlay");
  const enterBtn = document.getElementById("enter-btn");

  const enterApp = () => {
    controls.lock();
  };

  if (clickOverlay) {
    clickOverlay.addEventListener("click", enterApp);
  }
  if (enterBtn) {
    enterBtn.addEventListener("click", enterApp);
  }

  eventBus.on("pointerlock:change", (isLocked: any) => {
    if (clickOverlay) {
      if (isLocked) {
        clickOverlay.classList.add("hidden");
      } else {
        clickOverlay.classList.remove("hidden");
      }
    }
  });

  // Load Scene Manifest (points to public/scenes/home-01/scene.json)
  const sceneUrl = "/scenes/home-01/scene.json";
  const manifest = await sceneManager.loadScene(sceneUrl, loading);

  // Connect bounds controller to controls
  const bounds = sceneManager.getBoundsController();
  if (bounds) {
    controls.setBoundsController(bounds);
  }

  // Set spawn position
  controls.setSpawn(manifest.spawn.position, manifest.spawn.yaw_deg, manifest.eye_height_m);

  // Animation Loop with delta time
  let lastTimestamp = performance.now();

  function animate(timestamp: number) {
    requestAnimationFrame(animate);

    const deltaTime = (timestamp - lastTimestamp) / 1000;
    lastTimestamp = timestamp;

    controls.update(deltaTime);
    hud.update(timestamp);
    sceneManager.render();
  }

  requestAnimationFrame(animate);
}

window.addEventListener("DOMContentLoaded", () => {
  init().catch((err) => {
    console.error("Failed to initialize VYTRIX viewer:", err);
  });
});
