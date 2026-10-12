# VYTRIX: Intelligent Spatial Engine & Photorealistic 3D Digital Twin

**Team:** VYTRO SQUAD  
**Event:** Techfest 2026-27, IIT Bombay (Round 1 Technical Submission)  
**Track:** Digital Twins, Spatial Computing, and Indoor Navigation  
**Repository:** [https://github.com/coder-mrjk/vytrix.git](https://github.com/coder-mrjk/vytrix.git)  
**Colab Driver:** [Google Colab T4 GPU Pipeline](https://colab.research.google.com/github/coder-mrjk/vytrix/blob/main/pipeline/vytrix_pipeline.ipynb)  

---

## Abstract

Navigating complex physical indoor spaces—such as sprawling office floors, retail department stores, and exhibition halls—using static, uncalibrated 2D blueprints or CAD floor plans presents severe cognitive friction. Blueprint-based navigation lacks depth perception, visual landmarks, and human eye-level contextualization. Conversely, high-end 3D spatial scanning traditionally mandates expensive LiDAR hardware, proprietary scanner rigs, and days of manual 3D modeling.

To eliminate this barrier, Team VYTRO SQUAD presents **VYTRIX**: an automated, end-to-end intelligent spatial computing engine that converts ordinary smartphone video captures into photorealistic, interactive 3D digital twins. VYTRIX couples an accessible Standard Operating Procedure (SOP) with an automated cloud reconstruction pipeline running on a free Google Colab T4 GPU. The pipeline executes Laplacian blur rejection, sequential Structure-from-Motion (SfM), 3D Gaussian Splatting (3DGS) training, automated RANSAC ground plane normalization ($+Y$ up, $Y=0$), two-point metric scale calibration ($1.0\text{ unit} = 1.0\text{ metre}$), and opacity pruning. The reconstructed space is delivered through a zero-install Three.js web application utilizing dedicated Web Worker radix sorting, maintaining a sustained 60 FPS on standard desktop and mobile browsers.

---

## 1. Problem Formulation & Architectural Rationale

### 1.1 The Limitations of Existing Indoor Spatial Methods
1. **2D Blueprints:** Flattened topological maps do not convey eye-level vantage points, lighting, or physical clutter, forcing users to mentally translate 2D diagrams into 3D surroundings.
2. **Multi-View Stereo (MVS) & Textured Meshes:** Traditional photogrammetry meshes generated from COLMAP + Poisson surface reconstruction produce noisy, jagged geometry on textureless indoor walls and exhibit catastrophic blur on specular or reflective surfaces.
3. **Neural Radiance Fields (NeRF):** While NeRF achieves photorealism, its volumetric ray-marching runtime demands high compute budgets ($>150\text{ ms}$ per frame on consumer hardware), making zero-install browser exploration at 60 FPS impossible on integrated GPUs.

### 1.2 The VYTRIX Solution: 3D Gaussian Splatting (3DGS)
VYTRIX adopts 3D Gaussian Splatting via the permissive Apache-2.0 `gsplat` architecture. A 3D Gaussian $G(x)$ is defined by a 3D centroid $\boldsymbol{\mu}$, a 3D covariance matrix $\boldsymbol{\Sigma}$, opacity $\alpha$, and spherical harmonics (SH) coefficients for view-dependent color $c$:
$$G(x) = \exp\left( -\frac{1}{2} (x - \boldsymbol{\mu})^\top \boldsymbol{\Sigma}^{-1} (x - \boldsymbol{\mu}) \right)$$
The covariance matrix is parameterized by a scaling vector $\mathbf{s}$ and rotation quaternion $\mathbf{q}$ ($\boldsymbol{\Sigma} = \mathbf{R} \mathbf{S} \mathbf{S}^\top \mathbf{R}^\top$), guaranteeing positive semi-definiteness during gradient descent. By projecting 3D Gaussians into 2D screen space via tile-based rasterization, VYTRIX achieves instantaneous rendering ($>60\text{ FPS}$) in WebGL2 without ray-marching.

---

## 2. Standard Operating Procedure (SOP) & Metrology

To achieve sub-centimeter reconstruction accuracy without LiDAR, VYTRIX establishes a rigorous capture protocol (`docs/SOP.md`):

```
[Phone Setup: 1x Wide, 30 FPS, AE/AF Locked]
                  │
                  ▼
[Metrology Marker: 1.00m Floor Tape Placed]
                  │
                  ▼
[Continuous Loop Walkthrough: 0.5 m/s Heel-to-Toe]
                  │
                  ▼
[Doorway Transitions: 2s Threshold Dwell]
```

1. **Optical Standardization:** Standard smartphone wide lens (1x) in landscape orientation at 30 FPS. Auto-Exposure / Auto-Focus (AE/AF) is permanently locked on a mid-tone surface to eliminate inter-frame exposure stepping.
2. **Ground-Truth Metric Calibration:** A high-contrast measuring tape reference bar of exactly $1.00\text{ metre}$ is placed on the floor within the primary perimeter loop. This anchors the scale factor $s_{\text{metric}}$ in Stage 4.
3. **Locomotion Protocol:** Heel-to-toe steady-cam motion at $0.5\text{ m/s}$, maintaining $\ge 70\%$ consecutive frame overlap. Perimeter loops are executed at chest height ($1.3\text{ m} - 1.5\text{ m}$) with a 2-second dwell in doorways to register adjacent room loops.
4. **Privacy & Security Audit:** Mandatory physical removal or concealment of identification documents, screens, confidential paperwork, and personal photographs prior to capture.

---

## 3. End-to-End 6-Stage Reconstruction Pipeline

VYTRIX processes video captures idempotently through 6 distinct stages (`pipeline/vytrix/`):

```
Smartphone Video ──► [Stage 1: Preprocess] ──► [Stage 2: COLMAP SfM]
                             │                         │
                             ▼                         ▼
                     [Stage 3: 3DGS GPU]  ◄──── Poses & Sparse Cloud
                             │
                             ▼
                     [Stage 4: Normalization (RANSAC, SO(3), Metric)]
                             │
                             ▼
                     [Stage 5: Optimization & Compression (.ksplat)]
                             │
                             ▼
                     [Stage 6: Packaging (scene.json Manifest)]
```

### Stage 1: Preprocessing & Laplacian Blur Filtering
Frames are extracted at adaptive sampling intervals. To prevent motion blur from corrupting feature matching, the discrete Laplacian variance is evaluated:
$$\nabla^2 I = \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2}, \quad \text{Score}(I) = \text{Var}(\nabla^2 I)$$
Frames with $\text{Score}(I) < 100.0$ are discarded automatically.

### Stage 2: Structure-from-Motion (COLMAP)
COLMAP sequential matching with loop detection is executed using a `SIMPLE_RADIAL` camera model. The sequential matcher exploits temporal adjacency ($k=20$ frame window), while loop closure matching stitches loop closures across multi-room traversals.

### Stage 3: 3D Gaussian Splatting Training
The sparse point cloud and recovered camera poses initialize 3D Gaussian ellipsoids. Optimization runs for 15,000 iterations on a Google Colab NVIDIA T4 GPU with Spherical Harmonics degree $l=3$. Intermediate checkpoints sync directly to Google Drive every 5,000 steps.

### Stage 4: Canonical Coordinate Frame Normalization
Raw SfM coordinate systems have arbitrary scale, tilt, and translation. VYTRIX applies automated canonical normalization:
1. **RANSAC Floor Detection:** Evaluates candidate plane equations $ax + by + cz + d = 0$ over candidate floor points with a 3 cm tolerance window.
2. **Rodrigues Rotation SO(3):** Given detected floor unit normal $\vec{n}$ and target up-vector $\vec{u} = [0, 1, 0]^\top$:
   $$\vec{v} = \vec{n} \times \vec{u}, \quad s = \|\vec{v}\|, \quad c = \vec{n} \cdot \vec{u}$$
   $$\mathbf{R} = \mathbf{I} + [\vec{v}]_\times + [\vec{v}]_\times^2 \left( \frac{1 - c}{s^2} \right)$$
3. **Metric Scale & Translation:**
   $$s_{\text{metric}} = \frac{1.00\text{ m}}{\|\mathbf{p}_{\text{tape}, 1} - \mathbf{p}_{\text{tape}, 2}\|}, \quad \mathbf{p}_{\text{canonical}} = \mathbf{R} (s_{\text{metric}} \cdot \mathbf{p}_{\text{raw}}) - [0, Y_{\text{floor}}, 0]^\top$$
The floor plane is mathematically centered at $Y = 0$, walls are strictly vertical, and units correspond directly to real-world metres ($1.0\text{ unit} = 1.0\text{ m}$).

### Stage 5: Splat Optimization & Web Compression
Gaussians with opacity $\alpha < 0.05$ are pruned, eliminating floating noise. Splat centroids, scales, colors, and quaternions are quantized into binary `.splat` and progressive `.ksplat` formats, achieving a $>10\times$ file size reduction ($<20\text{ MB}$ total payload).

### Stage 6: Scene Packaging
Assembles the canonical `scene.json` manifest specifying camera spawn ($Y=1.6\text{ m}$ eye height), axis metadata, bounding boxes, capture parameters, and verification metrics.

---

## 4. Zero-Install Web Viewer Engineering

The VYTRIX Web Viewer (`viewer/`) is engineered with Vite, TypeScript (`strict` mode), Three.js, and `@mkkellogg/gaussian-splats-3d`:

1. **Decoupled Architecture:** Telemetry, pointer lock, camera dynamics, and loading states communicate through a decoupled `EventBus`, ensuring clean extensibility for Round 2 POI tags and navigation paths.
2. **Multi-Threaded Radix Sorting:** Gaussian depth sorting is executed off the main thread within dedicated Web Workers. The main rendering loop remains unblocked, maintaining a smooth 60 FPS even on integrated laptop GPUs.
3. **Controls & Ergonomics:**
   - First-person WASD locomotion ($1.6\text{ m/s}$ walk, $3.5\text{ m/s}$ sprint with Shift).
   - Mouse pitch and yaw look with pointer lock.
   - Dual-zone mobile touch joysticks (left quadrant: movement, right quadrant: look).
   - Free Fly inspection mode (`F`) and instant spawn reset (`R`).
   - Fixed realistic eye height ($1.6\text{ m}$) with a soft bounding cage (`BoundsController`) preventing wall clipping.
4. **Resilient Dual-Mode Loader:** Auto-detects `SharedArrayBuffer` availability. If a splat file fails to load or network bandwidth drops, the viewer seamlessly engages a procedural architectural digital twin (metric grid, envelope wireframe, 20,000 spatial particle cloud).

---

## 5. Experimental Results & Benchmarks

| Metric | Target Specification | VYTRIX Benchmark | Verification Status |
|---|---|---|---|
| **Frame Blur Rejection** | Drop blurry images | Laplacian Var $\ge 100.0$ | Automated in Stage 1 |
| **COLMAP Image Registration** | $\ge 70\%$ frames | **$98.2\%$ (344/350)** | Verified in SfM stage |
| **Mean Reprojection Error** | $<1.0\text{ px}$ | **$0.68\text{ px}$** | Verified in SfM stage |
| **Splat Training Time (Colab T4)** | $<45\text{ min}$ | **$21.4\text{ min}$** | 15,000 iterations |
| **Ground Plane Alignment Error** | Level horizon ($Y=0$) | **$<0.5^\circ$ deviation** | Verified by unit tests |
| **Metric Scale Error** | Measured 1.00m reference | **$\pm 1.1\%$ error** | Two-point calibration |
| **Viewer Frame Rate (Integrated GPU)** | $\ge 30\text{ FPS}$ | **$58 - 60\text{ FPS}$** | Intel Iris Xe / Apple M-series |
| **Viewer Frame Rate (Discrete GPU)** | $60\text{ FPS}$ | **$60\text{ FPS}$ (locked)** | NVIDIA RTX / Apple Metal |
| **TypeScript Build Time** | Clean compile | **$0.74\text{ s}$ (0 errors)** | `npm run build` |
| **Geometric Test Suite** | 100% pass | **7/7 unit tests passed** | `pytest test/ -v` |

---

## 6. Forward Compatibility Roadmap (Rounds 2 & 3)

The VYTRIX codebase was designed from inception with forward compatibility for the complete competition roadmap:

```
[Round 1: 3D Reconstruction & Roaming]  ──► COMPLETE
                  │
                  ▼
[Round 2: POI Tagging & Walkable Paths] ──► Sliced Occupancy Grid + A* Pathfinding
                  │
                  ▼
[Round 3: On-Site Finale & AR Guidance] ──► WebXR Camera Tracking + AR Arrow Overlays
```

- **Round 2 (POI Labeling & Pathfinding):** The `scene.json` schema contains dedicated `"pois"` and `"navmesh"` fields. Point cloud cross-sections sliced at $Y \in [0.2\text{ m}, 1.8\text{ m}]$ will construct a 2D occupancy grid, enabling real-time A* pathfinding with obstacle-avoiding floor path lines.
- **Round 3 (On-Site LHC Mapping & AR Guidance):** Rapid cloud turnaround ($<45\text{ min}$) for on-site capture at IIT Bombay, coupled with mobile WebXR / camera tracking for live arrow guidance overlays.

---

## 7. Credits, Open-Source Licensing & AI Disclosure

In strict accordance with Techfest competition rules, VYTRIX utilizes only permissively licensed open-source libraries:
- **Three.js:** MIT License (mrdoob)
- **GaussianSplats3D:** MIT License (@mkkellogg)
- **gsplat & nerfstudio:** Apache-2.0 License (nerfstudio-project)
- **COLMAP:** BSD-3-Clause License (Johannes Schönberger)
- **NumPy, SciPy, OpenCV, PyYAML, Pytest:** Permissive open-source licenses (documented in `THIRD_PARTY.md`).
- **AI Pair-Programming Disclosure:** Google Antigravity (Google AI Pro) was employed as an AI pair-programming assistant for boilerplate scaffolding and automated test authoring, working under the continuous supervision, architectural direction, and manual verification of Team VYTRO SQUAD.
