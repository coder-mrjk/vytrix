# VYTRIX Demonstration Video Screenplay & Shot List (3–5 Minutes)

**Competition:** Techfest 2026-27, IIT Bombay (Round 1)  
**Team:** VYTRO SQUAD  
**Deliverable:** 3 to 5-minute video detailing project scope, capture process, and showing the 3D web walkthrough.  
**Target Duration:** **3 minutes 45 seconds** (225 seconds — well within the 180s–300s window).  

---

## Shot List & Timing Table

| Segment | Timestamp | Duration | Visual On-Screen | Spoken Narration / Audio |
|---|---|---|---|---|
| **1. Intro & Scope** | 0:00 – 0:30 | 30 s | Title card: *VYTRIX: Intelligent Spatial Engine* by *VYTRO SQUAD*. Problem statement slides showing clumsy 2D blueprints vs photorealistic 3D digital twins. | "Welcome to VYTRIX, developed by Team VYTRO SQUAD for the spatial digital twin challenge at Techfest IIT Bombay. Navigating complex indoor environments using static 2D blueprints is unintuitive. VYTRIX turns ordinary smartphone video captures into photorealistic, interactive 3D digital twins viewable anywhere in a browser with zero installs." |
| **2. Capture SOP** | 0:30 – 1:30 | 60 s | Live footage of operator holding phone at chest level, 1x wide lens, AE/AF locked. B-roll of measuring tape 1.00m floor calibration marker, slow walking pace (0.5 m/s), perimeter loops, and 2-second pause in doorway threshold. | "Our Standard Operating Procedure enables anyone to capture spaces without specialized LiDAR sensors. Key rules include locked auto-exposure to prevent flashing, maintaining diffuse ambient lighting, walking at half a meter per second with over 70% frame overlap, and traversing doorways smoothly to stitch adjacent rooms. We place a 1.00-meter tape reference on the floor for ground-truth metric scaling." |
| **3. Pipeline & Colab** | 1:30 – 2:15 | 45 s | Screencast of Colab notebook: GPU validation, frame extraction with Laplacian blur filtering, COLMAP sequential matching, 3DGS training, and RANSAC ground plane normalization. | "Our 6-stage reconstruction pipeline runs seamlessly on a free Google Colab T4 GPU. Stage 1 extracts sharp frames and rejects motion-blurred images. Stage 2 executes COLMAP sequential feature matching. In Stage 3, we train 3D Gaussian Splats with checkpoints synced to Google Drive. Stage 4 applies RANSAC plane fitting to align gravity with plus-Y and scale the environment metrically." |
| **4. Live 3D Walkthrough** | 2:15 – 3:15 | 60 s | Live screen recording of browser in incognito mode. Seamless WASD movement, mouse look, sprint with Shift, entering different rooms, inspecting details, HUD showing 60 FPS, coordinates, and toggling Fly Mode with key F. | "Here is the live VYTRIX web viewer built with Vite, TypeScript, and Three.js. Notice the fluid 60 frames-per-second performance with zero plugin installs. Standard WASD controls and mouse pointer-lock let users explore naturally. The camera stays fixed at a realistic eye height of 1.6 meters, with soft bounding cages preventing clipping through walls. Pressing 'F' unlocks free-flight mode for judge inspection." |
| **5. Conclusion & Roadmap** | 3:15 – 3:45 | 30 s | Architecture summary slide, metrics overview (sub-20MB ksplat, 30+ FPS on integrated GPUs), and roadmap for Round 2 POI tagging and navigation. | "By compressing our splats into web-optimized binary format, the entire digital twin loads in under 15 seconds. All data structures are forward-compatible for Round 2 POI tagging and pathfinding. Thank you to Techfest IIT Bombay for this opportunity!" |

---

## Recording Tips for the Operator

1. **Screen Resolution:** Record the web viewer screen at 1080p (1920x1080) at 60 FPS.
2. **Audio:** Use a clear microphone with minimal background noise.
3. **Cursor:** Ensure mouse cursor disappears cleanly when pointer lock is engaged.
4. **Duration Check:** Double-check final rendered video file is between **3:00 and 5:00** before uploading to Google Drive.
