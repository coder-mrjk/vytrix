# VYTRIX: Intelligent Spatial Engine & Photorealistic 3D Digital Twin

[![Techfest IIT Bombay](https://img.shields.io/badge/Techfest_2026--27-IIT_Bombay-00f0ff?style=for-the-badge)](https://techfest.org)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/coder-mrjk/vytrix/blob/main/pipeline/vytrix_pipeline.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](THIRD_PARTY.md)
[![TypeScript: Strict](https://img.shields.io/badge/TypeScript-Strict-blue?logo=typescript)](viewer/tsconfig.json)

> **Team:** VYTRO SQUAD  
> **Challenge:** Techfest 2026-27, IIT Bombay (Round 1)  
> **Repository:** [https://github.com/coder-mrjk/vytrix.git](https://github.com/coder-mrjk/vytrix.git)

---

## 1. Overview

**VYTRIX** is an end-to-end intelligent spatial computing engine that transforms ordinary smartphone video captures of real indoor environments into photorealistic, interactive 3D digital twins. It replaces static 2D blueprints with an automated, gravity-aligned, metrically scaled spatial environment viewable in any modern desktop browser with zero plugin installation.

### Key Capabilities:
- **Smartphone-Only Capture:** Standard Operating Procedure (SOP) tailored for standard wide cameras (no LiDAR required).
- **Automated Colab GPU Pipeline:** Idempotent, resumable 6-stage reconstruction using COLMAP sequential feature matching and Apache-2.0 3D Gaussian Splatting (`gsplat`).
- **Canonical Coordinate Frame Normalization:** Automated RANSAC ground plane fitting to guarantee floor alignment ($Y = 0$), vertical wall leveling ($+Y$ up), and two-point metric scaling ($1\text{ unit} = 1\text{ metre}$).
- **Zero-Install Web Viewer:** Multi-threaded Three.js + Web Workers viewer maintaining 60 FPS with fluid WASD + mouse roaming, soft bounding cages, and real-time HUD telemetry.

---

## 2. System Architecture

```
[Smartphone Video (MP4)] + capture_meta.json
         │
         ▼
[Stage 1: Preprocess]    Adaptive decimation & Laplacian blur filtering
         │
         ▼
[Stage 2: SfM Poses]     COLMAP sequential matching + loop closure
         │
         ▼
[Stage 3: Splat Train]   3D Gaussian Splatting on GPU + Google Drive sync
         │
         ▼
[Stage 4: Normalize]     RANSAC ground plane (+Y up, Y=0), metric scale
         │
         ▼
[Stage 5: Optimize]      Opacity pruning (<0.05) & .ksplat quantization
         │
         ▼
[Stage 6: Package]       scene.json manifest + web assets bundle
         │
         ▼
[Web Viewer]             Zero-install Vite + TypeScript + Three.js
```

---

## 3. Quickstart: Web Viewer (Zero-Install Local Run)

To run the interactive 3D digital twin locally:

### Prerequisites:
- Node.js (v18+) & npm

### Steps:
```bash
# 1. Clone repository
git clone https://github.com/coder-mrjk/vytrix.git
cd vytrix/viewer

# 2. Install dependencies
npm install

# 3. Launch local development server
npm run dev
```

Open `http://localhost:3000` in Google Chrome, Microsoft Edge, or Mozilla Firefox.

### Controls:
- **Click Screen:** Lock mouse cursor and begin exploration.
- **W / A / S / D:** Walk forward, left, backward, right.
- **Mouse:** Free look (pitch & yaw).
- **Shift:** Sprint ($3.0\text{ m/s}$).
- **F:** Toggle Free Fly inspection mode.
- **R:** Reset camera to spawn position.
- **Esc:** Release mouse pointer lock.

---

## 4. Reconstructing from Video (Google Colab GPU)

Judges and users can reproduce the complete 3D digital twin on a free Google Colab T4 GPU:

1. Click the **[Open in Colab](https://colab.research.google.com/github/coder-mrjk/vytrix/blob/main/pipeline/vytrix_pipeline.ipynb)** badge above.
2. Select **Runtime $\rightarrow$ Change runtime type $\rightarrow$ GPU (T4)**.
3. Follow the numbered cells to execute the pipeline:
   - **Cell 0–1:** GPU check and pinned dependency install.
   - **Cell 2–4:** Google Drive checkpoint mount and video selection.
   - **Cell 5:** Run full reconstruction:
     ```bash
     python -m vytrix.run --video "video.mp4" --config config.yaml
     ```
   - **Cell 6:** Download the generated `vytrix_scene_bundle.zip` and place it in `viewer/public/scenes/home-01/`.

---

## 5. Verification & Mathematical Testing

To verify the geometric normalization, Rodrigues rotation matrices, and RANSAC plane fitting:

```bash
# Using pytest
PYTHONPATH=pipeline pytest test/test_normalization.py -v
```

All geometric test suites pass with zero warnings.

---

## 6. Directory Structure

```
/
├── README.md               # Main documentation and reproduction guide
├── SPEC.md                 # Competition technical specification
├── AGENTS.md               # Standing quality and execution rules
├── DECISIONS.md            # Architecture Decision Records (ADRs)
├── THIRD_PARTY.md          # Dependency licenses and IP citations
├── config.yaml             # Central pipeline configuration parameters
├── pipeline/
│   ├── vytrix/             # Python reconstruction package
│   │   ├── preprocess.py   # Stage 1: Frame extraction & blur filtering
│   │   ├── sfm.py          # Stage 2: COLMAP pose estimation
│   │   ├── train.py        # Stage 3: 3DGS trainer wrapper
│   │   ├── normalize.py    # Stage 4: RANSAC floor leveling & metric scale
│   │   ├── optimize.py     # Stage 5: Splat pruning & compression
│   │   ├── package.py      # Stage 6: scene.json generation
│   │   └── run.py          # CLI runner
│   ├── vytrix_pipeline.ipynb # Google Colab pipeline driver notebook
│   └── requirements.txt    # Pinned Python dependencies
├── viewer/                 # Zero-install Vite + TypeScript + Three.js app
│   ├── src/
│   │   ├── scene/          # SceneManager & scene.json schema types
│   │   ├── controls/       # FirstPersonControls & BoundsController
│   │   ├── ui/             # HUD telemetry & LoadingOverlay
│   │   └── utils/          # Decoupled EventBus
│   └── public/scenes/      # Reconstructed digital twin models & manifests
├── test/
│   └── test_normalization.py # Geometric unit tests (RANSAC, rotation, scale)
└── docs/
    ├── SOP.md              # Capture Standard Operating Procedure checklist
    ├── ARCHITECTURE.md     # In-depth architectural designs and math
    ├── PERFORMANCE.md      # Browser FPS and memory profiling benchmarks
    ├── video_script.md     # 3 to 5-minute video presentation script
    └── submission_checklist.md # Official submission verification
```

---

## 7. Credits & License Compliance

- **Team:** VYTRO SQUAD (Engineering, Capture SOP, System Architecture, Testing)
- **Three.js:** MIT License ([mrdoob/three.js](https://github.com/mrdoob/three.js))
- **GaussianSplats3D:** MIT License ([@mkkellogg/gaussian-splats-3d](https://github.com/mkkellogg/GaussianSplats3D))
- **gsplat & nerfstudio:** Apache-2.0 License ([nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat))
- **COLMAP:** BSD-3-Clause ([colmap/colmap](https://colmap.github.io/))
- **AI Coding Assistance:** Google Antigravity (Google AI Pro) assisted under direct supervision and continuous manual verification by VYTRO SQUAD.
- Full details documented in [`THIRD_PARTY.md`](THIRD_PARTY.md).
