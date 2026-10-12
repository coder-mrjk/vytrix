# SPEC.md: VYTRIX Technical Specification

**Project:** VYTRIX (Intelligent Spatial Computing Engine)  
**Team:** VYTRO SQUAD  
**Challenge:** Techfest 2026-27, IIT Bombay (Round 1)  
**Track:** Digital Twins, Spatial Computing, and Indoor Navigation  
**Repository:** [https://github.com/coder-mrjk/vytrix.git](https://github.com/coder-mrjk/vytrix.git)  

---

## 1. Executive Summary & Objective

**VYTRIX** is an end-to-end intelligent spatial computing platform that transforms ordinary smartphone video captures of real-world indoor spaces into photorealistic, interactive 3D digital twins. It replaces static, outdated 2D blueprints with an automated, gravity-aligned, metrically scaled spatial environment viewable in any modern desktop browser with zero plugin installation.

### The Challenge Statement (Techfest 2026-27, IIT Bombay)
> *"How would you design and build a complete software pipeline that turns ordinary smartphone photos or videos of an indoor space into an interactive 3D web application: one that lets remote users freely explore the space in first person, search for a specific room or item and jump straight to it, and see the best walking path to reach it around real physical obstacles?"*

---

## 2. End-to-End User Experience

A non-technical user must be able to:
1. **Capture:** Record a standard indoor space (home, office floor, retail store) using a standard smartphone camera following our Standard Operating Procedure (SOP).
2. **Reconstruct:** Process the video through an automated cloud pipeline on a free Google Colab T4 GPU with zero manual 3D modeling.
3. **Explore Remotely:** Open a single web link to freely roam the space in first person with fluid WASD and mouse look controls.
4. **Search & Navigate (Round 2):** Select Points of Interest (POIs) such as "Reception" or "Meeting Room 4" and follow an optimal, obstacle-aware walking path rendered directly on the floor.
5. **AR Navigation (Round 3 / Bonus):** Navigate on-site using phone camera tracking with directional guidance overlays.

---

## 3. Competition Structure & Deliverables

### Round 1: 3D Reconstruction & Roaming (Online — Deadline: 31 Oct 2026)
- **Focus:** SOP construction, automated 3D model building, and free-roaming web viewer.
- **Test Dataset:** Participant's own home (or accessible indoor space).
- **Deliverables:** Google Drive folder link ("Anyone with the link can view") containing:
  1. `Technical_Abstract_VYTRIX.pdf` (max 5 pages) covering architecture, pipeline, SOP, and mathematics.
  2. Proof of Concept & Web Viewer Link document.
  3. Demonstration Video (3 to 5 minutes, target 3m 45s).
  4. Code Repository with setup instructions and sample data in `test/`.
  5. Master PDF (`Additional_Links_and_Prototypes.pdf`) containing all URLs.

### Round 2: POIs & Desktop Navigation (Online — Deadline: 30 Nov 2026)
- **Focus:** POI spatial indexing, search UI, and obstacle-avoiding floor pathfinding.
- **Deliverables:** Updated repository branch, live web app with interactive POIs & navigation, and 3–5 minute demonstration video.

### Round 3: On-Site Capture & Live Finale (IIT Bombay Campus — 16–17 Dec 2026)
- **Focus:** On-site mapping and live deployment of an assigned campus venue (e.g. Lecture Hall Complex - LHC).
- **Day 1:** Field data collection and cloud pipeline execution.
- **Day 2:** 10-minute live pitch and platform demo + 5-minute technical Q&A with judges.
- **Bonus:** On-site mobile AR camera navigation (qualifies team for Juspay full-time opportunities).

---

## 4. System Architecture

```
[Smartphone 4K/1080p Video] + Floor Tape Reference (1.00m)
          │
          ▼
[Stage 1: Preprocess]       Decimation & Laplacian blur rejection (score >= 100.0)
          │
          ▼
[Stage 2: Structure-from-Motion] COLMAP sequential matcher + loop closure
          │
          ▼
[Stage 3: 3D Gaussian Splatting] gsplat GPU rasterizer + Drive checkpoints
          │
          ▼
[Stage 4: Normalization]    RANSAC floor plane (+Y up, Y=0), metric scale (1m = 1 unit)
          │
          ▼
[Stage 5: Optimization]     Opacity pruning (<0.05), .ksplat quantization
          │
          ▼
[Stage 6: Packaging]        scene.json manifest + web asset bundle
          │
          ▼
[Zero-Install Web Viewer]   Vite + TypeScript + Three.js + Web Workers
```

---

## 5. Capture Standard Operating Procedure (SOP) Specifications

1. **Hardware:** Standard smartphone with optical image stabilization (OIS) and standard wide lens (1x). No LiDAR required.
2. **Camera Configuration:** Landscape orientation, 30 FPS, locked exposure/focus (AE/AF lock) to eliminate exposure flicker.
3. **Scale Calibration Target:** Exactly $1.00\text{ m}$ painter's tape target placed on the floor to establish metric scale.
4. **Walking Protocol:** Heel-to-toe slow pace ($0.5\text{ m/s}$), continuous overlapping perimeter loops, camera held at chest height ($1.3\text{ m}$ to $1.5\text{ m}$), 2-second pause in doorway thresholds.
5. **Lighting & Privacy:** Diffuse interior lighting; mandatory privacy audit removing sensitive documents, screens, and personal photos.

---

## 6. Mathematical Foundations

### 6.1. Motion Blur Filtering (Discrete Laplacian Variance)
$$\nabla^2 I(x, y) = \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2}$$
$$\text{Score}(I) = \text{Var}(\nabla^2 I) = \frac{1}{N} \sum_{x, y} \left( \nabla^2 I(x, y) - \mu_{\nabla^2} \right)^2$$
Frames with $\text{Score}(I) < 100.0$ are automatically dropped from the SfM feature matching set.

### 6.2. Floor Plane Fitting (RANSAC)
The dominant horizontal floor plane $ax + by + cz + d = 0$ is estimated via RANSAC with normal unit vector $\vec{n} = [a, b, c]^\top$.

### 6.3. Gravity Alignment (Rodrigues Rotation SO(3))
Aligns detected normal $\vec{n}$ with the canonical up-vector $\vec{u} = [0, 1, 0]^\top$:
$$\vec{v} = \vec{n} \times \vec{u}, \quad s = \|\vec{v}\|, \quad c = \vec{n} \cdot \vec{u}$$
$$[\vec{v}]_\times = \begin{bmatrix} 0 & -v_z & v_y \\ v_z & 0 & -v_x \\ -v_y & v_x & 0 \end{bmatrix}$$
$$\mathbf{R} = \mathbf{I} + [\vec{v}]_\times + [\vec{v}]_\times^2 \left( \frac{1 - c}{s^2} \right)$$

### 6.4. Metric Scaling & Translation
$$s_{\text{metric}} = \frac{d_{\text{real}}}{d_{\text{SfM}}} = \frac{1.00\text{ m}}{\|\mathbf{p}_{\text{tape}, 1} - \mathbf{p}_{\text{tape}, 2}\|}$$
$$\mathbf{p}_{\text{canonical}} = \mathbf{R} (s_{\text{metric}} \cdot \mathbf{p}_{\text{raw}}) - [0, Y_{\text{floor}}, 0]^\top$$

---

## 7. Web Viewer Specifications

- **Tech Stack:** Vite + TypeScript (`strict` mode) + Three.js + `@mkkellogg/gaussian-splats-3d`.
- **Target Performance:** Sustained $\ge 55$ FPS on integrated GPUs; $\ge 60$ FPS on discrete GPUs.
- **Controls:**
  - `W / A / S / D`: Walk forward, left, backward, right ($1.6\text{ m/s}$).
  - `Shift`: Sprint multiplier ($2.2\times = 3.52\text{ m/s}$).
  - Mouse: Free pitch and yaw look with pointer lock.
  - `F`: Toggle free fly inspection mode.
  - `R`: Reset to canonical spawn location.
  - Mobile Touch: Dual on-screen virtual touch controllers (drag left for translation, drag right for camera look).
- **Camera Configuration:** Canonical eye-height $Y = 1.6\text{ m}$, FOV $75^\circ$.
- **Bounds Protection:** Soft bounding box cage (`BoundsController`) prevents escaping the reconstructed room envelope.
- **HUD Telemetry:** Real-time FPS, frame time (ms), 3D position coordinates $[X, Y, Z]$, look angles, and active splat count.
- **Resilient Fallback:** Automatically falls back to a high-fidelity synthetic digital twin room (metric grid, wireframe cage, 20,000 spatial particles) if splat binary fails or is unavailable.

---

## 8. Data Model Specification (`scene.json`)

```json
{
  "schema_version": "1.0",
  "scene_id": "home-01",
  "title": "VYTRIX Reconstructed Space",
  "units": "metres",
  "up_axis": "+Y",
  "handedness": "right",
  "splat": {
    "file": "scene.ksplat",
    "format": "ksplat",
    "num_gaussians": 350000,
    "bytes": 18500000
  },
  "transform_applied": {
    "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    "scale_method": "two_point_tape",
    "scale_error_pct": 1.1
  },
  "bounds": {
    "min": [-4.5, 0.0, -5.0],
    "max": [4.5, 2.8, 5.0]
  },
  "spawn": {
    "position": [0.0, 0.0, 0.0],
    "yaw_deg": 0
  },
  "eye_height_m": 1.6,
  "capture": {
    "device": "Smartphone (Wide Camera, 4K 30fps)",
    "date": "2026-10-10",
    "fps": 30,
    "num_frames_used": 350
  },
  "metrics": {
    "registered_images": 344,
    "total_images": 350,
    "reproj_error_px": 0.68,
    "psnr": 30.2,
    "ssim": 0.924
  },
  "collision_proxy": null,
  "navmesh": null,
  "pois": [],
  "credits": [
    "VYTRO SQUAD (Team)",
    "Techfest 2026-27, IIT Bombay",
    "gsplat & nerfstudio (Apache-2.0)",
    "Three.js & @mkkellogg/gaussian-splats-3d (MIT)"
  ]
}
```

---

## 9. Forward Compatibility (Rounds 2 & 3)

### Round 2: POI Labeling & Obstacle-Aware Pathfinding
- **POI Schema:** Array of `{ "id": string, "name": string, "position": [x, y, z] }`.
- **Navigation Grid:** 2D occupancy grid rasterized from sparse point cloud sliced at $Y \in [0.2\text{ m}, 1.8\text{ m}]$.
- **Pathfinder:** A* / Breadth-First search computing non-colliding waypoints on the floor plane.
- **Visual Path:** Three.js animated glowing floor spline guiding user to destination.

### Round 3: Live Finale & AR Guidance
- Fast turnaround Colab runner optimized for $<45$ minute reconstruction.
- Mobile WebXR / camera overlay with directional arrows guiding on-site users.

---

## 10. Licensing & Intellectual Property Compliance

- All third-party software must be permissively licensed (MIT, Apache-2.0, BSD-3-Clause).
- Non-commercial / research-only licenses (e.g. original Inria 3DGS) are prohibited.
- AI pair-programming assistance (Google Antigravity under Google AI Pro) is explicitly disclosed in the Technical Abstract and repository.
- Full credits maintained in `THIRD_PARTY.md`.

---

## 11. Security & Privacy Safeguards

- Reconstructed models and video captures must not reveal personally identifiable information (PII), faces, passwords, financial records, or medical information.
- Pre-capture physical audit required per `docs/SOP.md`.

---

## 12. Verification & Quality Gates

- `npm run build` must compile with TypeScript `strict` mode with zero errors.
- Geometric normalization unit tests (`pytest test/test_normalization.py -v`) must pass 4/4.
- All pipeline stages must be idempotent and resumable.
- Web viewer must achieve $\ge 55$ FPS on integrated GPUs without tab blocking.

---

## 13. Project Milestones

Per `AGENTS.md` Rule 1: **One milestone at a time. Do not proceed to the next milestone until the user approves.**

- **Milestone 1: Specification & Core Pipeline Integrity**
  - Create root `SPEC.md`.
  - Fix pipeline imports (`import numpy as np` in `pipeline/vytrix/run.py`).
  - Configure Python virtual environment on macOS and verify 4/4 unit tests.
- **Milestone 2: Cloud Reconstruction Infrastructure**
  - Implement reproducible Google Colab driver notebook (`pipeline/vytrix_pipeline.ipynb`).
- **Milestone 3: Sample Data Package & Splat Assets**
  - Provide sample dataset in `test/data/`.
  - Provide initial 3D Gaussian Splat model in `viewer/public/scenes/home-01/scene.splat`.
- **Milestone 4: Official Submission Deliverables**
  - Author Technical Abstract PDF draft (`docs/TECHNICAL_ABSTRACT.md`).
  - Author Master Submission Document (`docs/MASTER_SUBMISSION_DOCUMENT.md`).
- **Milestone 5: Edge Deployment & Final Verification**
  - Deploy viewer to edge hosting.
  - Audit against `docs/submission_checklist.md`.
