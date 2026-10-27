# VYTRIX Round 1 Master Factsheet & Production Audit

**Competition:** Techfest 2026-27, IIT Bombay (Round 1 Online Submission)  
**Track:** Digital Twins, Spatial Computing, and Indoor Navigation  
**Team Name:** VYTRO SQUAD  
**Date:** 27 October 2026  
**Round 1 Deadline:** 31 October 2026 (Internal Target: 29 October 2026)  
**Repository:** [https://github.com/coder-mrjk/vytrix.git](https://github.com/coder-mrjk/vytrix.git)  
**Branch:** `main`  
**Latest Verified Commit:** `06b9a61`  
**License:** MIT (Permissive open-source)

---

## 1. Status Audit of 9 Core Round 1 Deliverables

| # | Audit Item | Status | Verified Evidence in Repository | Blocker / What Must Be Provided |
|---|---|---|---|---|
| **1** | **Real Reconstruction Results** | `NOT DONE` | `viewer/public/scenes/home-01/scene.splat` is the 213,760 byte (6,680 Gaussian) synthetic placeholder. `scene.json` metrics are null (`reproj_error_px: null`, `psnr: null`, `ssim: null`). | **User Action:** Run `pipeline/vytrix_pipeline.ipynb` on Google Colab T4 GPU with real home video. |
| **2** | **Live Web Viewer Deployment** | `NOT DONE` | `viewer/public/_headers` created with COOP/COEP headers; no active Cloudflare Pages or Vercel URL deployed. | **User Action:** Run `npm --prefix viewer run build` and deploy `viewer/dist` to Cloudflare Pages (or link repo). |
| **3** | **GitHub Repository State** | `DONE` | Verified public via `gh repo view` (`isPrivate: false`, `visibility: "PUBLIC"`). Remote `git@github.com:coder-mrjk/vytrix.git` up-to-date with `origin/main`. Tracked repo size ~564 KiB; zero files over 50 MB (largest file: 208 KiB). | None. (If real `.splat` exceeds 50 MB, configure Git LFS before pushing). |
| **4** | **Demo Video (3–5 min)** | `NOT DONE` | No video files (`.mp4`, `.mov`, `.webm`) exist in repository. Script prepared in `docs/video_script.md` (4m 30s target). | **User Action:** Record 3–5 min screencast + phone capture, upload to YouTube as Unlisted, paste link into master doc. |
| **5** | **The Real Capture Session** | `NOT DONE` | `test/data/capture_meta.json` marked `"synthetic placeholder"`. No real phone capture metadata logged. | **User Action:** Record home walkthrough per `docs/SOP.md` (1m floor tape, 30 FPS wide lens, locked AE/AF) and log device specs. |
| **6** | **Viewer Performance Benchmarks** | `NOT MEASURED` | `docs/PERFORMANCE.md` replaced with strict `TODO(measured)` template and step-by-step measurement guide. | **User Action:** Walk in viewer on user machine, read HUD FPS / DevTools Network & Memory, fill `PERFORMANCE.md`. |
| **7** | **Screenshots of Real Scene** | `NOT DONE` | Zero real scene screenshots exist in `docs/` or `viewer/public/` (only competition slide grabs). | **User Action:** Capture 3–4 clean screenshots while roaming reconstructed room (no private info or screens) and save to `docs/screenshots/`. |
| **8** | **Team & Institutional Details** | `PARTLY` | Team Name `VYTRO SQUAD` recorded across all docs. Team ID, member names, and institute are missing. | **User Action:** Provide Team Registration ID, full member names, and Institute/College name. |
| **9** | **Known Problems with Scan** | `PARTLY` | Algorithmic safeguards implemented: `ScalePicker.ts` rejects upward clicks; floor RANSAC uses camera up-vector. Real physical defects unknown. | **User Action:** Inspect reconstructed real model for floaters near mirrors, holes in blank walls, or boundary clip. |

---

## 2. Real Metrics Table (Current State vs Target)

| Metric | Source File | Current Value in Repo | Target Requirement |
|---|---|---|---|
| **Gaussian Count** | `viewer/public/scenes/home-01/scene.json` | `6,680` (synthetic placeholder) | `TODO(measured: real Colab training output)` |
| **Splat File Size** | `viewer/public/scenes/home-01/scene.splat` | `213,760 bytes (0.20 MB)` | `TODO(measured: target < 50 MB)` |
| **Registered Frames** | `data/work/sfm/sfm_metrics.json` | `NOT DONE (null)` | `TODO(measured: ≥ 70% of extracted frames)` |
| **Reprojection Error** | `data/work/sfm/sfm_metrics.json` | `NOT DONE (null)` | `TODO(measured: < 1.0 px)` |
| **Training Steps** | `data/work/train/train_metrics.json` | `NOT DONE (null)` | `TODO(measured: 15,000 steps on T4)` |
| **Training Duration** | `data/work/train/train_metrics.json` | `NOT DONE (null)` | `TODO(measured: Colab elapsed seconds)` |
| **Floor Inliers** | `data/work/normalize/normalization_manifest.json` | `NOT DONE (null)` | `TODO(measured: inlier ratio ≥ 0.20)` |
| **Scale Method** | `viewer/public/scenes/home-01/scene.json` | `"two_point_tape"` | Verified via 2-point floor tape calibration |
| **Scale Error %** | `viewer/public/scenes/home-01/scene.json` | `null` | `TODO(measured: target < 3%)` |
| **PSNR / SSIM** | `viewer/public/scenes/home-01/scene.json` | `null` | `TODO(measured: only if output by trainer)` |

---

## 3. Team Details Checklist

- **Team Name:** `VYTRO SQUAD`
- **Competition:** Techfest 2026-27, IIT Bombay
- **Team ID:** `NOT DONE / missing: <Please provide your official Techfest Team ID>`
- **Team Members:** `NOT DONE / missing: <Please provide full names of all team members>`
- **College / Institute:** `NOT DONE / missing: <Please provide your college/institute name>`

---

## 4. Software Dependencies, Versions & Licenses

All third-party libraries utilized in VYTRIX carry permissive open-source licenses compatible with competition and commercial distribution. **Zero non-commercial or research-only licenses are present.**

### Frontend Web Viewer (`viewer/package.json`):
| Dependency | Version | License | Commercial Use | Purpose |
|---|---|---|---|---|
| **three** | `^0.160.0` | MIT | Permitted | Core 3D WebGL rendering engine |
| **@mkkellogg/gaussian-splats-3d** | `^0.4.5` | MIT | Permitted | Radix sort & 3D Gaussian Splat rasterization |
| **vite** | `^5.0.0` | MIT | Permitted | Fast frontend bundler and dev server |
| **typescript** | `^5.2.2` | Apache-2.0 | Permitted | Type-safe application development |

### Python Reconstruction Pipeline (`pipeline/requirements.txt`):
| Dependency | Version | License | Commercial Use | Purpose |
|---|---|---|---|---|
| **numpy** | `>=1.24.0,<2.0.0` | BSD-3-Clause | Permitted | Numerical arrays and matrix algebra |
| **scipy** | `>=1.11.0` | BSD-3-Clause | Permitted | Spatial KD-tree and Rodrigues rotation |
| **opencv-python-headless** | `>=4.8.0` | Apache-2.0 | Permitted | Video decoding & Laplacian blur variance |
| **pyyaml** | `==6.0.1` | MIT | Permitted | Configuration parsing |
| **pytest** | `>=7.4.0` | MIT | Permitted | Automated unit test suite |
| **ruff** | `>=0.6.0` | MIT / Apache-2.0 | Permitted | Linting and code style enforcement |

### Core Reconstruction Backends:
| Tool / Framework | Verified Version | License | Commercial Use | Purpose |
|---|---|---|---|---|
| **COLMAP** | `3.8+` (apt) | BSD-3-Clause | Permitted | Feature extraction, sequential SfM, and pose estimation |
| **gsplat** | `1.4.0` `TODO(verify)` | Apache-2.0 | Permitted | Differentiable Gaussian Splatting rasterizer |
| **PyTorch** | `2.1+` (Colab) | Modified BSD | Permitted | CUDA tensor computations & JIT compilation |
| **FFmpeg** | `4.4+` (apt) | LGPL / GPL | Permitted | Video stream frame extraction |

> [!NOTE]
> **License Compliance Confirmation:** No proprietary, research-only (e.g. Non-Commercial CC-BY-NC), or GPL-copyleft core libraries are linked into the public web viewer. All web distribution is pure MIT and Apache-2.0.
