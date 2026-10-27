# VYTRIX Web Viewer Performance & Profiling Benchmarks

**Project:** VYTRIX  
**Team:** VYTRO SQUAD  
**Specification:** `SPEC.md` Section 4 (D1–D3) & Section 9  
**Status:** `TEMPLATE - PENDING USER MEASUREMENT` (Do not commit unmeasured numbers)

---

## 1. Test Device & Environment

Fill this table with your physical measurement hardware before logging numbers:

| Property | Measured Value |
|---|---|
| **Device Model** | `TODO(measured: e.g. Apple MacBook Pro 14" / Custom Desktop)` |
| **CPU** | `TODO(measured: e.g. Apple M2 Pro / Intel Core i7-13700H)` |
| **GPU** | `TODO(measured: e.g. Apple M2 Pro 16-core GPU / NVIDIA RTX 4060)` |
| **Operating System** | `TODO(measured: e.g. macOS Sonoma 14.5 / Windows 11 23H2)` |
| **Browser & Version** | `TODO(measured: e.g. Google Chrome 130.0.6723.70)` |
| **Display Resolution** | `TODO(measured: e.g. 2560x1600 @ 120 Hz)` |
| **Network Connection** | `TODO(measured: e.g. Home Wi-Fi 6 (150 Mbps download))` |

---

## 2. Benchmark Acceptance Results

| Metric | Target (Integrated GPU) | Target (Discrete GPU) | Measured Result | Status |
|---|---|---|---|---|
| **Average Frame Rate (Walking)** | $\ge 30\text{ FPS}$ | $\ge 60\text{ FPS}$ | `TODO(measured)` FPS | `TODO(measured: PASS / FAIL)` |
| **Minimum Frame Rate (1% Low)** | $\ge 24\text{ FPS}$ | $\ge 45\text{ FPS}$ | `TODO(measured)` FPS | `TODO(measured: PASS / FAIL)` |
| **Average Frame Time** | $\le 33.3\text{ ms}$ | $\le 16.6\text{ ms}$ | `TODO(measured)` ms | `TODO(measured: PASS / FAIL)` |
| **Initial Splat Download Size** | $< 100\text{ MB}$ | $< 100\text{ MB}$ | `TODO(measured)` MB | `TODO(measured: PASS / FAIL)` |
| **Time to First Render (Broadband)** | $< 5\text{ s}$ | $< 5\text{ s}$ | `TODO(measured)` s | `TODO(measured: PASS / FAIL)` |
| **Time to First Render (Fast 4G)** | $< 20\text{ s}$ | $< 20\text{ s}$ | `TODO(measured)` s | `TODO(measured: PASS / FAIL)` |
| **JS Heap Memory** | $< 250\text{ MB}$ | $< 250\text{ MB}$ | `TODO(measured)` MB | `TODO(measured: PASS / FAIL)` |
| **Main Thread Freezing (Sort)** | $0\text{ ms}$ blocking | $0\text{ ms}$ blocking | `TODO(measured)` ms | `TODO(measured: PASS / FAIL)` |

---

## 3. Step-by-Step Measurement Procedures

### Procedure A: Frame Rate (FPS) and Frame Time
1. Open the viewer in a clean Incognito browser window with extensions disabled.
2. Enter exploration mode by clicking anywhere on the canvas.
3. Observe the bottom-left **HUD Telemetry** overlay:
   - Walk continuously around the entire room using WASD for 60 seconds.
   - Note the average FPS and frame time displayed in the HUD.
4. *Validation via Chrome DevTools:*
   - Press `F12` (or `Cmd+Option+I` on macOS) $\rightarrow$ Press `Cmd+Shift+P` $\rightarrow$ Type `Show frames per second (FPS) meter`.
   - Record the steady-state FPS graph and 1% low values.

### Procedure B: Time to First Render (TTFR)
1. Open Chrome DevTools $\rightarrow$ Select the **Network** tab.
2. Check **Disable cache**.
3. **Broadband Test (Unthrottled):**
   - Set Throttling dropdown to `No throttling`.
   - Hard refresh (`Cmd+Shift+R` or `Ctrl+F5`).
   - Note total time until the loading screen disappears and 3D splats appear on screen.
4. **Fast 4G Throttling Test:**
   - In DevTools Network tab, set Throttling dropdown to `Fast 4G` (download ~1.6 MB/s, upload ~750 KB/s, 560ms RTT).
   - Hard refresh.
   - Verify that the streamed percentage progress bar updates smoothly.
   - Record total elapsed time until the scene becomes interactive.

### Procedure C: Memory Footprint (JS Heap & VRAM)
1. In Chrome DevTools, open the **Performance monitor** tab (`Cmd+Shift+P` $\rightarrow$ `Show Performance monitor`).
2. Roam through the scene for 2 minutes while observing:
   - **JS heap size (MB)**: Record initial value after load and peak value after roaming.
   - Check that heap memory stabilizes without sawtooth spikes or runaway leaks.

### Procedure D: Main Thread Responsiveness (Radix Sort Worker)
1. In Chrome DevTools, open the **Performance** tab.
2. Click **Record** and aggressively rotate the camera 360 degrees for 5 seconds to force continuous depth re-sorting.
3. Stop the recording and inspect the **Main** thread flame chart:
   - Verify there are no red "Long Task" blocks (> 50 ms) attributed to splat sorting.
   - Confirm that radix sort runs inside dedicated Web Workers off the main thread.
