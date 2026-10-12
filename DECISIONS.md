# DECISIONS.md: Architecture Decision Records (ADRs)

Project: **VYTRIX**  
Team: **VYTRO SQUAD**  
Competition: **Techfest 2026-27, IIT Bombay (Round 1)**

---

## ADR-001: 3D Reconstruction Technique (3D Gaussian Splatting)
- **Date:** 2026-10-10
- **Decision:** Use 3D Gaussian Splatting (3DGS) via `gsplat` / `splatfacto` architecture rather than traditional NeRF or Photogrammetry Textured Meshes.
- **Alternatives Considered:**
  1. *Traditional MVS / Textured Mesh (COLMAP + OpenMVS / Poisson Reconstruction):* Produces noisy indoor meshes with holes on flat/reflective walls, low photorealism, and blurred textures.
  2. *NeRF (Instant-NGP / Nerfstudio):* High photorealism but requires volumetric ray-marching at runtime; cannot maintain 60 FPS in zero-install browser on low-end integrated GPUs.
  3. *Inria Gaussian Splatting (Original codebase):* Uses a non-commercial research license that poses competition licensing risks.
- **Why:** 3DGS produces photorealistic real-time rendering at 60+ FPS in browsers via WebGL2/WebGPU rasterizers with permissive Apache-2.0 / MIT licensing.

---

## ADR-002: Web Viewer Architecture (Vite + TypeScript + Three.js + Web Workers)
- **Date:** 2026-10-10
- **Decision:** Build the zero-install web viewer with Vite, TypeScript in strict mode, Three.js, and `@mkkellogg/gaussian-splats-3d` with dedicated Web Worker sorting.
- **Alternatives Considered:**
  1. *PlayCanvas Splat Viewer:* Capable, but Three.js ecosystem provides tighter integration with custom FirstPersonControls, HUD, scene graph manipulation, and future POI/pathfinding mesh layers for Rounds 2 & 3.
  2. *Antimatter15 WebGL Splat Viewer:* Minimalist, but lacks progressive stream loading, octree culling, and typed scene graph abstraction.
- **Why:** `@mkkellogg/gaussian-splats-3d` is MIT-licensed, actively maintained, supports streamed progressive chunk loading (`.ksplat` / `.splat`), multi-threaded CPU/GPU radix sorting, and runs smoothly on integrated GPUs without tab freezes.

---

## ADR-003: Cloud Training & Compute Infrastructure (Google Colab Free T4 + Drive Sync)
- **Date:** 2026-10-10
- **Decision:** Execute heavy GPU stages (COLMAP feature matching and 3DGS rasterization training) on Google Colab (T4 GPU, 16GB VRAM) backed by automated Google Drive checkpointing.
- **Alternatives Considered:**
  1. *Local GPU Execution:* Not feasible as the user workstation lacks a discrete NVIDIA CUDA GPU.
  2. *Cloud VM Instances (GCP / RunPod):* Incurs monetary cost, whereas the pipeline must be 100% free and reproducible by Techfest judges using free Google accounts.
- **Why:** Colab T4 is freely accessible to judges and participants. Idempotent stage resumes and Drive checkpointing protect against session disconnects.

---

## ADR-004: Canonical Scene Coordinate Frame Normalization
- **Date:** 2026-10-10
- **Decision:** Standardize scene coordinates to a strict Right-Handed canonical system:
  - Up axis: $+Y$
  - Floor plane: $Y = 0$
  - Units: metres ($1.0\text{ unit} = 1.0\text{ metre}$)
  - Camera eye-height: $1.6\text{ m}$ above floor
- **Alternatives Considered:**
  1. *Arbitrary SfM / COLMAP coordinate system:* Causes crooked horizons, inverted floors, and breaks any future floor navmesh or collision physics in Rounds 2 & 3.
  2. *Interactive manual rotation widget in viewer:* Inconsistent, not automated, and fails the reproducible pipeline requirements.
- **Why:** Automated RANSAC ground plane fitting on the sparse point cloud guarantees a level floor and vertical walls, providing forward compatibility for 2D obstacle grids and POI tagging.

---

## ADR-005: Hosting & Content Delivery
- **Date:** 2026-10-10
- **Decision:** Deploy the static viewer on free hosting (Cloudflare Pages / Firebase Hosting) with model assets streamed over HTTP with CORS headers.
- **Alternatives Considered:**
  1. *GitHub Pages alone:* Has a strict ~100MB per-file limit and bandwidth caps.
  2. *Self-hosted Node server:* Requires ongoing server maintenance and is prone to cold boots.
- **Why:** Cloudflare Pages and Firebase Hosting are completely free, offer high global edge bandwidth, and support progressive chunk streaming.
