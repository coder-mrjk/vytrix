# VYTRIX: Intelligent Spatial Engine & Photorealistic 3D Digital Twin

[![Techfest IIT Bombay](https://img.shields.io/badge/Techfest_2026--27-IIT_Bombay-00f0ff?style=for-the-badge)](https://techfest.org)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/coder-mrjk/vytrix/blob/main/pipeline/vytrix_pipeline.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](THIRD_PARTY.md)
[![TypeScript: Strict](https://img.shields.io/badge/TypeScript-Strict-blue?logo=typescript)](viewer/tsconfig.json)

> **Team:** VYTRO SQUAD  
> **Challenge:** Techfest 2026-27, IIT Bombay (Round 1)  
> **Repository:** [https://github.com/coder-mrjk/vytrix.git](https://github.com/coder-mrjk/vytrix.git)  
> **Branch:** `main`  
> **Target Space:** Indoor Physical Living Space / Digital Twin

---

## 1. Overview

**VYTRIX** is an open-source, automated intelligent spatial computing engine that reconstructs photorealistic, metrically calibrated 3D digital twins from standard smartphone video walkthroughs. It eliminates the requirement for proprietary LiDAR sensors by uniting a rigorous Standard Operating Procedure (SOP), automated Structure-from-Motion (COLMAP), 3D Gaussian Splatting (`gsplat`), canonical floor plane leveling (RANSAC), two-point metric scale calibration, and a zero-install Three.js web viewer.

---

## 2. System Architecture

```
[Smartphone Video (MP4)] + 1m Floor Reference Tape
         │
         ▼
[Stage 1: Preprocess]    Adaptive decimation & Laplacian variance blur filter
         │
         ▼
[Stage 2: SfM Poses]     COLMAP sequential/exhaustive matching + sub-model selection
         │
         ▼
[Stage 3: Splat Train]   gsplat rasterizer training on Colab T4 GPU + Drive checkpoints
         │
         ▼
[Stage 4: Normalize]     Camera-up-vector guided RANSAC floor leveling (+Y up, Y=0)
         │               and two-point metric scaling (1.0 unit = 1.0 metre)
         │
         ▼
[Stage 5: Optimize]      Opacity pruning (<0.05) & 32-byte binary .splat packing
         │
         ▼
[Stage 6: Package]       Evidence-based scene.json manifest & viewer asset bundle
         │
         ▼
[Web Viewer (PoC)]       Zero-install Vite + TypeScript + Three.js + Web Workers
```

---

## 3. Google Colab GPU Reconstruction Guide

Judges and evaluators can reproduce the entire reconstruction on a free Google Colab T4 GPU instance using the driver notebook [`pipeline/vytrix_pipeline.ipynb`](pipeline/vytrix_pipeline.ipynb).

### Step-by-Step Execution:

1. Open the driver notebook by clicking the **[Open in Colab](https://colab.research.google.com/github/coder-mrjk/vytrix/blob/main/pipeline/vytrix_pipeline.ipynb)** badge.
2. Select **Runtime $\rightarrow$ Change runtime type $\rightarrow$ T4 GPU**.
3. Execute the notebook cells in numerical order:

- **Step 1: GPU & Hardware Verification**
  Verifies CUDA availability and reports GPU VRAM (NVIDIA T4 with ~15–16 GB memory).

- **Step 2: Install System & Python Dependencies**
  Installs `colmap`, `ffmpeg`, `ninja-build` via `apt`, pinned Python dependencies (`pyyaml==6.0.1`, `numpy>=1.24.0,<2.0.0`, `scipy>=1.11.0`, `opencv-python-headless>=4.8.0`, `pytest>=7.4.0`), and `gsplat==1.4.0` `TODO(verify)`.

- **Step 3: Mount Google Drive**
  Mounts Google Drive (`/content/drive/MyDrive/VYTRIX_Checkpoints`) to safeguard training checkpoints against session timeouts.

- **Step 4: Clone Codebase & Run Unit Tests**
  Clones the official repository and runs the test suite (`PYTHONPATH=pipeline pytest test/ -v`) to confirm geometric and packaging routines pass.

- **Step 5: Dry-Run Pipeline Validation (Smoke Test)**
  Runs a rapid end-to-end smoke test on a short 30–60 second smartphone clip across all 6 stages (extracting 30 frames, 200 training steps).
  *(Note: Timings below are illustrative examples, NOT measured; each stage evaluates strictly measured pass/fail conditions):*
  ```text
  [PASS] Stage 1 (Preprocess): Extracted 30 frames
  [PASS] Stage 2 (COLMAP SfM): 28/30 images registered
  [PASS] Stage 3 (3DGS Training): 200 steps & CUDA compilation passed
  [PASS] Stage 4 (Normalization): Floor leveled to Y=0
  [PASS] Stage 5 (Optimize): 32-byte .splat binary created
  [PASS] Stage 6 (Packaging): Manifest generated
  ```

- **Step 6: Full Capture Video Ingestion**
  Upload your continuous smartphone video walkthrough recorded per [`docs/SOP.md`](docs/SOP.md) (slow loop, locked exposure/focus, 1m floor tape visible).

- **Step 7: Execute Full Reconstruction & Two-Pass Scale Calibration**
  - **Pass 1 (Full Reconstruction):** Runs all 6 stages uncalibrated (`python -m vytrix.run --video "$video_path" --config "config.yaml" --work-dir "data/work" --force`).
    > **Disconnect Resumption Policy:** Use `--force` **ONLY** for the first full run on a fresh directory. Never use `--force` when resuming after a Colab disconnect or session restart; without `--force`, the pipeline automatically detects existing stage manifests, skips completed stages, and resumes cleanly.
  - **Scale Calibration in Viewer:** Download the uncalibrated bundle from Step 8, open in the local web viewer, press **`P`** to activate Scale Calibration Mode, look down at the two endpoints of your 1-metre floor tape, click both points, verify real distance is `1.00`, and click **COPY CLI ARGUMENTS**.
  - **Pass 2 (Fast Recalibration without Retraining):** Set `RUN_PASS_2 = True`, paste `--scale-points` into `SCALE_POINTS`, and rerun Step 7. Stages 1–3 are skipped, Stage 3 output (`splat_raw.ply`) is reused directly without retraining, and Stages 4–6 rescale the model to exact real-world metres in ~15–20 seconds.

- **Step 8: Inspect Real Metrics & Download Bundle**
  Inspects measured metrics in `scene.json` (registered frames, reprojection error, Gaussian count, `.splat` size) and downloads `vytrix_scene_bundle.zip`.

---

## 4. Local Web Viewer (Zero-Install Roaming)

The VYTRIX interactive viewer is built with Vite, TypeScript, Three.js, and `@mkkellogg/gaussian-splats-3d`.

### Prerequisites:
- Node.js (v18+) and `npm`

### Local Setup & Launch:
```bash
# 1. Navigate to viewer directory
cd viewer

# 2. Install dependencies
npm install

# 3. (Optional) Place your reconstructed scene bundle into viewer/public/scenes/home-01/
#    If unpopulated, the viewer displays a local wireframe development room.

# 4. Start local development server
npm run dev
```

Open `http://localhost:3000` in Google Chrome, Microsoft Edge, or Mozilla Firefox.

### Controls:
- **Click Overlay / Enter:** Lock pointer and begin exploration.
- **W / A / S / D:** Walk forward, left, backward, right.
- **Mouse:** Look around (pitch & yaw).
- **Shift (Hold):** Sprint mode ($3.0\text{ m/s}$).
- **F:** Toggle Free Fly inspection mode (no gravity/bounds constraints).
- **R:** Reset camera to canonical spawn position.
- **P:** Toggle interactive **Scale Calibration Mode** (aim at floor tape from above and click).
- **Esc:** Unlock mouse cursor.

---

## 5. Automated Verification & Testing

All geometric normalization, floor RANSAC, scale calibration, and file integrity routines are validated with automated unit tests:

```bash
# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements.txt

# Run full pytest test suite
PYTHONPATH=pipeline pytest test/ -v

# Run linter & formatter checks
ruff check pipeline/ test/

# Verify viewer build
cd viewer && npm run build
```

---

## 6. Directory Structure

```
vytrix/
├── README.md               # Main reproduction guide and overview
├── SPEC.md                 # Competition specification and acceptance criteria
├── AGENTS.md               # Standing rules for development and verification
├── DECISIONS.md            # Architecture Decision Records (ADRs)
├── THIRD_PARTY.md          # Dependency licenses, versions, and citations
├── config.yaml             # Central reconstruction pipeline configuration
├── pipeline/
│   ├── requirements.txt    # Pinned Python dependencies
│   ├── vytrix_pipeline.ipynb # Official Google Colab GPU driver notebook
│   └── vytrix/
│       ├── preprocess.py   # Stage 1: Frame decimation & blur filtering
│       ├── sfm.py          # Stage 2: COLMAP feature extraction & matching
│       ├── train.py        # Stage 3: gsplat training orchestration
│       ├── normalize.py    # Stage 4: Floor RANSAC & metric scale calibration
│       ├── optimize.py     # Stage 5: Opacity pruning & 32-byte .splat packing
│       ├── package.py      # Stage 6: Manifest packaging
│       ├── run.py          # Resumable CLI runner
│       ├── dry_run.py      # Rapid smoke test runner
│       └── calibrate_scale.py # Standalone CLI scale helper
├── viewer/                 # Zero-install Three.js web application
│   ├── index.html          # HTML entrypoint with HUD & overlay UI
│   ├── package.json        # Pinned viewer dependencies
│   ├── public/
│   │   ├── _headers        # Cloudflare Pages COOP/COEP headers
│   │   └── scenes/home-01/ # Digital twin model and scene.json manifest
│   └── src/
│       ├── main.ts         # Main initialization and render loop
│       ├── controls/       # FirstPersonControls & BoundsController
│       ├── scene/          # SceneManager & scene.json schema definitions
│       └── ui/             # HUD telemetry & ScalePicker
├── test/
│   ├── test_normalization.py # Rodrigues rotation & plane fitting tests
│   ├── test_pipeline_real.py  # Stage 2-6 fail-loud and Pass 2 tests
│   ├── test_sample_data.py   # Format validation for sample dataset
│   └── data/                 # Sample data directory for competition submission
└── docs/
    ├── ROUND1_FACTSHEET.md # Master evidence-based factsheet for Round 1
    ├── SOP.md              # Capture Standard Operating Procedure checklist
    ├── ARCHITECTURE.md     # Mathematical foundations and stage specifications
    ├── PERFORMANCE.md      # Performance benchmarking template and protocol
    ├── video_script.md     # 3 to 5-minute video presentation script
    └── MASTER_SUBMISSION_DOCUMENT.md # Master competition submission index
```

---

## 7. Credits & Third-Party Dependencies

- **Team:** VYTRO SQUAD (Engineering, Architecture, Capture SOP, Verification)
- **Three.js:** MIT License ([mrdoob/three.js](https://github.com/mrdoob/three.js))
- **GaussianSplats3D:** MIT License ([@mkkellogg/gaussian-splats-3d](https://github.com/mkkellogg/GaussianSplats3D))
- **gsplat & nerfstudio:** Apache-2.0 License ([nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat))
- **COLMAP:** BSD-3-Clause ([colmap/colmap](https://colmap.github.io/))
- **PyTorch:** Modified BSD License ([pytorch/pytorch](https://pytorch.org))
- **AI Pair-Programming Disclosure:** Google Antigravity (Google AI Pro) was used for boilerplate scaffolding and automated test authoring under the direct direction, prompt engineering, and manual verification of Team VYTRO SQUAD.
- Full citation table and license links are maintained in [`THIRD_PARTY.md`](THIRD_PARTY.md).
