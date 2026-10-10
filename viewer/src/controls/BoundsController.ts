import * as THREE from "three";

export class BoundsController {
  private box: THREE.Box3;
  private enabled: boolean = true;
  private padding: number = 0.2; // 20cm buffer inside bounding box

  constructor(bounds: { min: [number, number, number]; max: [number, number, number] }) {
    this.box = new THREE.Box3(
      new THREE.Vector3(bounds.min[0], bounds.min[1], bounds.min[2]),
      new THREE.Vector3(bounds.max[0], bounds.max[1], bounds.max[2])
    );
  }

  public setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  public clampPosition(position: THREE.Vector3): void {
    if (!this.enabled) return;

    position.x = THREE.MathUtils.clamp(
      position.x,
      this.box.min.x + this.padding,
      this.box.max.x - this.padding
    );
    position.z = THREE.MathUtils.clamp(
      position.z,
      this.box.min.z + this.padding,
      this.box.max.z - this.padding
    );
    // Y bounds check with buffer
    position.y = THREE.MathUtils.clamp(
      position.y,
      this.box.min.y,
      this.box.max.y + 0.5
    );
  }
}
