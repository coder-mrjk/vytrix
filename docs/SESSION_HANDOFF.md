# VYTRIX: Mac Migration & Session Handoff Guide

**Project:** VYTRIX  
**Team:** VYTRO SQUAD  
**Competition:** Techfest 2026-27, IIT Bombay (Round 1)  
**GitHub Repository:** [https://github.com/coder-mrjk/vytrix.git](https://github.com/coder-mrjk/vytrix.git) (Branch: `main`)  
**Date of Migration:** 10 October 2026  

---

## 1. Project State Summary

Everything built on the Windows PC is safely committed and synced to GitHub:
- **Repository Scaffold & Agent Protocols:** `AGENTS.md`, `SPEC.md`, `DECISIONS.md`, `THIRD_PARTY.md`, `config.yaml`.
- **Zero-Install Web Viewer (`viewer/`):**
  - Built with Vite + TypeScript (`strict`) + Three.js + `@mkkellogg/gaussian-splats-3d`.
  - First-person WASD + Mouse look + Sprint (Shift) + Fly mode (F) + Reset (R).
  - Mobile touch support enabled (touch drag on left = movement, touch drag on right = camera look).
  - Network host enabled (`0.0.0.0:3000`) for access across devices on local Wi-Fi.
  - Fail-safe loader with SharedArrayBuffer auto-fallback and procedural room backup.
  - Sample 3D Gaussian Splat scene (`scene.splat`, 6,680 Gaussians) verified and committed.
- **6-Stage Reconstruction Pipeline (`pipeline/vytrix/`):**
  - Preprocess (blur filter), SfM (COLMAP), Train (3DGS gsplat), Normalize (RANSAC floor, +Y up, metric scale), Optimize (.ksplat), Package (scene.json).
  - Google Colab Driver Notebook: `pipeline/vytrix_pipeline.ipynb` (GPU T4 + Drive sync).
- **Quality Gates:**
  - `npm run build` passed in 2.3s with 0 errors.
  - `pytest test/test_normalization.py -v` passed (4/4 tests).
- **Official Documentation:**
  - `docs/SOP.md` (Capture checklist)
  - `docs/ARCHITECTURE.md` (Math & system diagrams)
  - `docs/PERFORMANCE.md` (FPS & network benchmarks)
  - `docs/video_script.md` (3-5 minute video screenplay)
  - `docs/submission_checklist.md` (Round 1 Drive audit)

---

## 2. 3-Step Setup on your MacBook

### Step 1: Open Terminal on Mac & Install Node.js (if not already installed)
If you already have Node.js, skip this. Otherwise install via Homebrew or from [nodejs.org](https://nodejs.org/):
```bash
# Check if node is installed
node -v

# If not installed, use brew:
brew install node
```

### Step 2: Clone the Repository
```bash
git clone https://github.com/coder-mrjk/vytrix.git
cd vytrix
```

### Step 3: Run the Web Viewer
```bash
cd viewer
npm install
npm run dev
```
Open `http://localhost:3000` in Safari, Chrome, or Edge on your Mac. You can also view it on your phone via the Mac's Wi-Fi IP address!

---

## 3. How to Resume the Antigravity Chat on your MacBook

1. Open **Antigravity IDE** on your MacBook.
2. Sign in with your same Google account (Google AI Pro subscription).
3. Open the cloned folder `/path/to/vytrix` as your active workspace.
4. In the Antigravity chat, paste this prompt:

> *"Hi Antigravity! I have switched from my Windows PC to my MacBook. I am working on VYTRIX for Team VYTRO SQUAD (Techfest 2026-27, IIT Bombay - Round 1). Please read `AGENTS.md`, `SPEC.md`, and `docs/SESSION_HANDOFF.md` to see what has been built and what we are doing next."*

The agent on your Mac will immediately read the handoff file, recognize all architectural decisions, understand the full codebase, and continue right where we left off!
