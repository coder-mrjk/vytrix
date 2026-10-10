declare module "@mkkellogg/gaussian-splats-3d" {
  import * as THREE from "three";

  export interface ViewerOptions {
    threeScene?: THREE.Scene;
    camera?: THREE.PerspectiveCamera;
    renderer?: THREE.WebGLRenderer;
    useBuiltInControls?: boolean;
    selfDrivenMode?: boolean;
    progressiveLoad?: boolean;
    gpuAcceleratedSort?: boolean;
    sharedMemoryForWorkers?: boolean;
  }

  export interface SplatSceneOptions {
    splatAlphaRemovalThreshold?: number;
    showLoadingUI?: boolean;
    position?: [number, number, number];
    rotation?: [number, number, number, number];
    scale?: [number, number, number];
    onProgress?: (percent: number, percentLabel: string) => void;
  }

  export class Viewer {
    constructor(options?: ViewerOptions);
    addSplatScene(path: string, options?: SplatSceneOptions): Promise<void>;
    update(): void;
    render(): void;
    dispose(): void;
  }
}
