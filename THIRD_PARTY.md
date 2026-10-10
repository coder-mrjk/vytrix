# THIRD_PARTY.md: Third-Party Dependencies and License Inventory

This document tracks all external libraries, frameworks, tools, and algorithms used in **VYTRIX**, ensuring 100% compliance with Techfest IIT Bombay guidelines and intellectual property rules.

| Name | Version | License | Purpose / Role | Source / URL |
|---|---|---|---|---|
| **Three.js** | `^0.160.0` | MIT | Core WebGL 3D rendering engine, scene graph, camera math, and lighting. | [https://github.com/mrdoob/three.js](https://github.com/mrdoob/three.js) |
| **@mkkellogg/gaussian-splats-3d** | `^0.4.0` | MIT | 3D Gaussian Splatting WebGL/Three.js renderer with Web Worker sorting & `.ksplat` streaming. | [https://github.com/mkkellogg/GaussianSplats3D](https://github.com/mkkellogg/GaussianSplats3D) |
| **Vite** | `^5.0.0` | MIT | Fast frontend build tool and dev server. | [https://github.com/vitejs/vite](https://github.com/vitejs/vite) |
| **TypeScript** | `^5.3.0` | Apache-2.0 | Type safety in `strict` mode for web viewer architecture. | [https://github.com/microsoft/TypeScript](https://github.com/microsoft/TypeScript) |
| **COLMAP** | `>= 3.8` | BSD-3-Clause | Structure-from-Motion (SfM) camera pose estimation and sparse point cloud generation. | [https://colmap.github.io/](https://colmap.github.io/) |
| **gsplat / nerfstudio** | `>= 1.0.0` | Apache-2.0 | CUDA-accelerated Gaussian Splatting rasterization and optimization backend. | [https://github.com/nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat) |
| **OpenCV (`opencv-python-headless`)** | `>= 4.8.0` | Apache-2.0 | Laplacian variance computation for blur detection and image filtering. | [https://github.com/opencv/opencv-python](https://github.com/opencv/opencv-python) |
| **PyYAML** | `^6.0` | MIT | Configuration loader for `config.yaml`. | [https://pyyaml.org/](https://pyyaml.org/) |
| **NumPy** | `^1.24.0` | BSD-3-Clause | Matrix transformations, RANSAC plane fitting, and vector math. | [https://numpy.org/](https://numpy.org/) |
| **SciPy** | `^1.11.0` | BSD-3-Clause | Spatial transforms, Rotation matrices, and optimization routines. | [https://scipy.org/](https://scipy.org/) |
| **FFmpeg** | Binary CLI | LGPL / GPL | Video frame extraction and audio stripping. | [https://ffmpeg.org/](https://ffmpeg.org/) |
| **Google Antigravity** | Agentic AI | Google AI Pro | Pair-programming and architectural coding assistant (VYTRO SQUAD engineers directed all prompt engineering, architecture, and manual verification). | [https://deepmind.google](https://deepmind.google) |

---

## License Compliance Note
- **No Non-Commercial / Research-Only Code:** The original Inria 3D Gaussian Splatting codebase is explicitly avoided due to its non-commercial clause. We strictly employ Apache-2.0 and MIT implementations (`gsplat` and `@mkkellogg/gaussian-splats-3d`).
- **All third-party tools are properly credited** in the Technical Abstract and submission documentation.
