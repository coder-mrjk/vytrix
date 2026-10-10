export interface SceneManifest {
  schema_version: string;
  scene_id: string;
  title: string;
  units: "metres";
  up_axis: "+Y";
  handedness: "right";
  splat: {
    file: string;
    format: "splat" | "ksplat" | "spz";
    num_gaussians: number;
    bytes: number;
  };
  transform_applied: {
    matrix: number[]; // 4x4 column-major matrix
    scale_method: string;
    scale_error_pct: number;
  };
  bounds: {
    min: [number, number, number];
    max: [number, number, number];
  };
  spawn: {
    position: [number, number, number];
    yaw_deg: number;
  };
  eye_height_m: number;
  capture: {
    device: string;
    date: string;
    fps: number;
    num_frames_used: number;
  };
  metrics: {
    registered_images: number;
    total_images: number;
    reproj_error_px: number;
    psnr: number | null;
    ssim: number | null;
  };
  // Reserved for Rounds 2 & 3
  collision_proxy: unknown | null;
  navmesh: unknown | null;
  pois: Array<{
    id: string;
    name: string;
    position: [number, number, number];
  }>;
  credits: string[];
}
