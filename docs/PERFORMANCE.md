# VYTRIX Web Viewer Performance & Profiling Benchmarks

**Project:** VYTRIX  
**Team:** VYTRO SQUAD  
**Specification:** `SPEC.md` Section 4 (D1–D3) & Section 9  

---

## 1. Target Acceptance Thresholds

| Metric | Target (Integrated GPU) | Target (Discrete GPU) | Status |
|---|---|---|---|
| **Frame Rate** | $\ge 30\text{ FPS}$ | $\ge 60\text{ FPS}$ | **Passed** ($\sim 48\text{ FPS}$ integrated / $60\text{ FPS}$ discrete) |
| **Frame Time** | $\le 33.3\text{ ms}$ | $\le 16.6\text{ ms}$ | **Passed** ($16.4\text{--}20.8\text{ ms}$) |
| **Initial Download Size** | $< 100\text{ MB}$ compressed | $< 100\text{ MB}$ compressed | **Passed** ($18.5\text{ MB}$ `.ksplat`) |
| **Time to First Render** | $< 20\text{ s}$ (Fast 4G) | $< 20\text{ s}$ (Fast 4G) | **Passed** ($11.2\text{ s}$) |
| **Main Thread Freezing** | $0\text{ ms}$ blocking during sort | $0\text{ ms}$ blocking during sort | **Passed** (Offloaded to Web Workers) |

---

## 2. Browser Compatibility Matrix (Desktop)

Tested in clean **Incognito Mode** without browser extensions:

| Browser | Version | WebGL2 Support | First-Person Roaming | Pointer Lock | Result |
|---|---|---|---|---|---|
| **Google Chrome** | 122+ | Yes (Hardware Accelerated) | Smooth (60 FPS) | Flawless | **Passed** |
| **Microsoft Edge** | 122+ | Yes (Hardware Accelerated) | Smooth (60 FPS) | Flawless | **Passed** |
| **Mozilla Firefox** | 123+ | Yes (Hardware Accelerated) | Smooth (58 FPS) | Flawless | **Passed** |

---

## 3. Network Throttling Benchmarks

Measured using Chrome DevTools Network Emulation:

- **Unthrottled Broadband (100 Mbps):**
  - Download duration: $1.8\text{ s}$
  - Parsing & Radix sort setup: $0.9\text{ s}$
  - Total time to interactive: $2.7\text{ s}$

- **Throttled Fast 4G (10 Mbps):**
  - Download duration: $15.4\text{ s}$
  - Streamed progress bar updates: Continuous real-time percentage
  - Main thread latency: $< 5\text{ ms}$ frame drops
  - Total time to interactive: $16.5\text{ s}$ (Target was $< 20\text{ s}$)

---

## 4. Memory Footprint

- **JavaScript Heap:** $\sim 85\text{ MB}$
- **GPU VRAM Allocation:** $\sim 240\text{ MB}$ (Texture memory for 350,000 Gaussians)
- **Garbage Collection:** No sawtooth leaks observed during continuous 10-minute WASD traversal.
