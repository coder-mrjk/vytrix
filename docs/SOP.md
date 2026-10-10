# VYTRIX Standard Operating Procedure (SOP): Indoor Spatial Capture

**Project:** VYTRIX (Namma Space — Techfest 2026-27, IIT Bombay)  
**Target:** Non-technical operators capturing indoor environments with a smartphone for high-fidelity 3D Gaussian Splatting and metric digital twins.

---

## 1. Equipment Checklist

- [ ] **Smartphone:** Modern smartphone with primary wide lens and optical image stabilization (OIS).
- [ ] **Tape Measure & Painter's Tape:** For laying down a 1.00 m reference bar on the floor.
- [ ] **Lens Cleaning Cloth:** Microfiber cloth to thoroughly wipe all camera lenses.
- [ ] **Storage Space:** At least 5 GB of free phone storage.

---

## 2. Environment Preparation

1. **Privacy & Security Audit (Mandatory):**
   - The reconstructed 3D web model will be hosted publicly for competition judges.
   - **Remove or conceal:** Personal identification documents, credit cards, bank statements, computer screens displaying passwords or chats, personal family photographs, medication labels, and mail.
2. **Lighting:**
   - Turn **ON** all ambient ceiling and floor lights.
   - Ensure uniform, diffuse illumination. Avoid strong direct sunlight creating harsh moving shadows.
   - If large windows are present, capture on an overcast day or during dusk/evening with interior lights on.
3. **Doors & Pathways:**
   - Open all interior doors completely flat against the wall so doorways can be traversed seamlessly.
   - Secure or remove pets, and ensure no other individuals walk across the camera frame during capture.
4. **Reflective Surfaces:**
   - Close curtains over large reflective mirrors if possible, or avoid lingering directly in front of large mirrors.
5. **Texture Enhancements for Blank Walls:**
   - Large blank, textureless white walls can cause feature matching to fail in COLMAP.
   - If a hallway has bare white walls, place temporary small pieces of colored tape or sticky notes on the wall corners/edges to give the SfM matcher robust visual feature points.

---

## 3. Camera Settings

Configure your phone camera prior to tapping record:
- **Orientation:** Landscape mode (horizontal).
- **Resolution & Frame Rate:** 4K (3840x2160) or 1080p (1920x1080) at **30 FPS**.
- **Lens:** Standard 1x Wide lens (do **NOT** switch between ultrawide, telephoto, or macro while recording).
- **Exposure & Focus Lock:** Tap and hold on a mid-brightness area in the room to activate **AE/AF Lock** (Auto-Exposure / Auto-Focus Lock). This prevents rapid brightness flashing as you face windows.
- **HDR & Enhancements:** Turn **OFF** auto-HDR, night mode, portrait mode, and dynamic lens-switching.

---

## 4. Ground-Truth Scale Target (Metric Calibration)

To ensure the 3D model is metrically scaled in real-world metres ($1.00\text{ unit} = 1.00\text{ m}$):
1. Use a measuring tape to measure exactly **$1.00\text{ metre}$** on a clear section of the floor.
2. Place two contrasting strips of painter's tape on the floor marking the ends ($0.00\text{ m}$ and $1.00\text{ m}$).
3. When recording, make sure the camera films this floor marker clearly from at least 3 angles during your walkthrough.

---

## 5. Movement and Recording Protocol

> **Core Rule:** Smooth, steady, continuous motion. Avoid quick spins, sudden jerks, or running. Walk like a human steady-cam at approximately $0.5\text{ m/s}$ (slow heel-to-toe steps).

### Step-by-Step Trajectory
```
[Start at Room 1 Doorway] 
         │
         ▼
[Perimeter Pass 1: Walk perimeter facing inward towards room center]
         │
         ▼
[Perimeter Pass 2: Walk perimeter facing outward towards walls/corners]
         │
         ▼
[Center Sweep: 360° slow orbit at center of room]
         │
         ▼
[Doorway Transition: Pause 2 seconds, film both door jambs, step through]
         │
         ▼
[Room 2 Trajectory: Repeat perimeter and center passes]
         │
         ▼
[Loop Closure: Walk back through the doorway and finish at exact start position]
```

1. **Overlap Requirement (3-Ray Rule):** Every object and wall segment must be visible in at least **3 distinct camera positions** separated by roughly 15 to 30 degrees.
2. **Doorways & Transitions:**
   - Pause for 2 seconds at the threshold.
   - Film the door frame from inside the first room, step through slowly, and film back into the first room from the second room. This creates the visual bridge COLMAP needs to stitch both rooms into one unified coordinate frame.
3. **Loop Closure:**
   - Always return to your starting position and film your initial view before stopping the recording. This enables COLMAP's loop detector to eliminate drift and warp.
4. **Total Duration:**
   - For 1 to 2 rooms (25–40 m²), a single continuous video of **2 to 3 minutes** is optimal (generating ~300–450 sharp frames after decimation).

---

## 6. Capture Metadata File: `capture_meta.json`

Save this metadata file alongside your video before processing:

```json
{
  "scene_id": "home-01",
  "capture_date": "2026-10-11",
  "operator": "VYTRO SQUAD",
  "device": {
    "model": "Smartphone (Wide Camera)",
    "resolution": "1920x1080",
    "fps": 30,
    "stabilization": "OIS",
    "lens": "1x Wide"
  },
  "environment": {
    "num_rooms": 2,
    "approx_area_sqm": 30,
    "lighting": "Indoor ambient ceiling lights on, blinds closed"
  },
  "scale_ground_truth": {
    "type": "floor_tape_marker",
    "measured_distance_meters": 1.00,
    "notes": "Two blue tape marks on living room floor"
  }
}
```

---

## 7. Quality Verification & Common Mistakes

| Problem | Cause | How to Fix |
|---|---|---|
| **Blurry Gaussians / Smears** | Moving too fast or camera shake. | Walk slower ($0.5\text{ m/s}$), hold phone with two hands against chest, wipe lens. |
| **Disconnected Rooms** | Rushing through doorways without looking back. | Pause in doorway, film both rooms from the threshold, ensure 70%+ visual overlap. |
| **Floaters / Background Artifacts** | Mirrors or intense outdoor window backlight. | Pull curtains over windows, lock exposure (AE-Lock), avoid direct mirror reflections. |
| **Unregistered Images in COLMAP** | Blank textureless walls. | Stick small colored tape markers on bare corners to provide feature keypoints. |
