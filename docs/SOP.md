# VYTRIX Standard Operating Procedure (SOP): Indoor Spatial Capture

**Project:** VYTRIX  
**Team:** VYTRO SQUAD  
**Challenge:** Techfest 2026-27, IIT Bombay (Round 1)  
**Status:** `ACTIVE SPECIFICATION - PENDING PHYSICAL USER CAPTURE`  
**Purpose:** Instructions for capturing physical indoor spaces with a standard smartphone camera to generate high-fidelity 3D Gaussian Splats and metrically calibrated digital twins.

---

## 1. Physical Capture Status & Execution Checklist

Before submitting Round 1, the operator must verify compliance with every step below:

- [ ] **Physical Space Cleaned:** Personal documents, screens, mail, and family photos removed.
- [ ] **Ambient Lighting Fixed:** Overhead ceiling lights ON; window blinds closed to avoid dynamic backlighting.
- [ ] **1.00 m Floor Reference Placed:** Measured with a physical tape measure and marked with contrasting painter's tape on the floor.
- [ ] **Camera Locked:** Standard 1x wide lens; 1080p or 4K at 30 FPS; **AE/AF Lock engaged**.
- [ ] **Continuous Walkthrough Recorded:** Single slow continuous loop (~1.5–2.5 minutes) walking heel-to-toe at ~0.5 m/s.
- [ ] **Floor Tape Filmed from Above:** Marked floor tape filmed clearly from multiple angles to enable 3D ground intersection in the scale picker.
- [ ] **Loop Closure Completed:** Recording starts and finishes at the exact same location and orientation.
- [ ] **Video Transferred to Colab:** Uploaded directly to Google Colab via Step 6 of `pipeline/vytrix_pipeline.ipynb`.

---

## 2. Equipment Checklist

1. **Smartphone:** Standard smartphone with optical image stabilization (OIS) on primary wide camera (iPhone, Samsung, Pixel, OnePlus, etc.).
2. **Physical Tape Measure & Painter's Tape:** For placing an exact $1.00\text{ m}$ reference marker on the floor.
3. **Microfiber Cloth:** Clean all phone camera lenses thoroughly before recording.
4. **Storage:** At least 3–5 GB of free phone storage.

---

## 3. Environment Preparation

1. **Privacy & Security Audit (Mandatory):**
   - The reconstructed 3D web model will be hosted publicly for competition judges.
   - **Remove or conceal:** Personal identification cards, credit cards, bank statements, computer screens displaying passwords or chats, personal family photographs, medication labels, and mail.
2. **Lighting:**
   - Turn **ON** all ambient ceiling and floor lights.
   - Ensure uniform, diffuse illumination. Avoid strong direct sunlight creating harsh moving shadows.
   - If large windows are present, capture on an overcast day or during dusk/evening with interior lights on and blinds drawn.
3. **Doors & Pathways:**
   - Open all interior doors completely flat against the wall so doorways can be traversed seamlessly.
   - Secure or remove pets, and ensure no other individuals walk across the camera frame during capture.
4. **Reflective Surfaces:**
   - Close curtains over large reflective mirrors if possible, or avoid lingering directly in front of large mirrors.
5. **Texture Enhancements for Blank Walls:**
   - Large blank, textureless white walls can cause feature matching to fail in COLMAP.
   - If a hallway has bare white walls, place temporary small pieces of colored tape or sticky notes on the wall corners/edges to give the SfM matcher robust visual feature points.

---

## 4. Camera Settings

Configure your phone camera prior to tapping record:
- **Orientation:** Landscape mode (horizontal).
- **Resolution & Frame Rate:** 4K (3840x2160) or 1080p (1920x1080) at **30 FPS**.
- **Lens:** Standard 1x Wide lens (do **NOT** switch between ultrawide, telephoto, or macro while recording).
- **Exposure & Focus Lock:** Tap and hold on a mid-brightness area in the room to activate **AE/AF Lock** (Auto-Exposure / Auto-Focus Lock). This prevents rapid brightness flashing as you face windows.
- **HDR & Enhancements:** Turn **OFF** auto-HDR, night mode, portrait mode, and dynamic lens-switching.

---

## 5. Ground-Truth Scale Target (Metric Calibration)

To ensure the 3D model is metrically scaled in real-world metres ($1.00\text{ unit} = 1.00\text{ m}$):
1. Use a physical measuring tape to measure exactly **$1.00\text{ metre}$** on a clear section of the floor.
2. Place two contrasting strips of painter's tape on the floor marking the ends ($0.00\text{ m}$ and $1.00\text{ m}$).
3. When recording, make sure the camera films this floor marker clearly from above at multiple angles during your walkthrough.

---

## 6. Movement and Recording Protocol

> **Core Rule:** Smooth, steady, continuous motion. Avoid quick spins, sudden jerks, or running. Walk like a human steady-cam at approximately $0.5\text{ m/s}$ (slow heel-to-toe steps).

### Step-by-Step Trajectory
```
[Start at Room Doorway] 
         │
         ▼
[Perimeter Pass: Walk room boundary facing inward towards room center]
         │
         ▼
[Center Orbit: Slow 360° rotation from center of room]
         │
         ▼
[Scale Target Pass: Circle around 1.00m floor tape looking downward]
         │
         ▼
[Loop Closure: Walk back and finish at exact start position]
```

1. **Overlap Requirement (3-Ray Rule):** Every object and wall segment must be visible in at least **3 distinct camera positions** separated by roughly 15 to 30 degrees.
2. **Doorways & Transitions:**
   - Pause for 2 seconds at the threshold.
   - Film the door frame from inside the first room, step through slowly, and film back into the first room from the second room. This creates the visual bridge COLMAP needs to stitch both rooms into one unified coordinate frame.
3. **Loop Closure:**
   - Always return to your starting position and film your initial view before stopping the recording. This enables COLMAP's loop detector to eliminate drift and warp.
4. **Total Duration:**
   - For 1 to 2 rooms (20–40 m²), a single continuous video of **1.5 to 2.5 minutes** is optimal (generating ~300–450 sharp frames after decimation).

---

## 7. Capture Metadata Template: `capture_meta.json`

Save this metadata template alongside your video before processing:

```json
{
  "dataset_status": "TODO(user: real_home_capture)",
  "scene_id": "home-01",
  "capture_date": "TODO(user: YYYY-MM-DD)",
  "operator": "VYTRO SQUAD",
  "device": {
    "model": "TODO(user: e.g. iPhone 14 Pro)",
    "resolution": "TODO(user: e.g. 1920x1080 or 3840x2160)",
    "fps": 30,
    "stabilization": "OIS",
    "lens": "1x Wide"
  },
  "environment": {
    "room_type": "TODO(user: e.g. Living Room)",
    "approx_area_sqm": "TODO(user: e.g. 25)",
    "lighting": "Indoor ambient ceiling lights on, blinds closed"
  },
  "scale_ground_truth": {
    "type": "floor_tape_marker",
    "measured_distance_meters": 1.00,
    "notes": "Two contrasting painter tape marks on floor"
  }
}
```

---

## 8. Quality Verification & Common Mistakes

| Problem | Cause | How to Fix |
|---|---|---|
| **Blurry Gaussians / Smears** | Moving too fast or camera shake. | Walk slower ($0.5\text{ m/s}$), hold phone with two hands against chest, wipe lens. |
| **Disconnected Rooms** | Rushing through doorways without looking back. | Pause in doorway, film both rooms from threshold, ensure 70%+ visual overlap. |
| **Floaters / Background Artifacts** | Mirrors or intense outdoor window backlight. | Pull curtains over windows, lock exposure (AE-Lock), avoid direct mirror reflections. |
| **Unregistered Images in COLMAP** | Blank textureless walls. | Stick small colored tape markers on bare corners to provide feature keypoints. |
