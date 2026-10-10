export class LoadingOverlay {
  private overlayEl: HTMLElement | null;
  private fillEl: HTMLElement | null;
  private percentEl: HTMLElement | null;
  private statusEl: HTMLElement | null;
  private bytesEl: HTMLElement | null;

  constructor() {
    this.overlayEl = document.getElementById("loading-screen");
    this.fillEl = document.getElementById("progress-fill");
    this.percentEl = document.getElementById("progress-percent");
    this.statusEl = document.getElementById("loading-status");
    this.bytesEl = document.getElementById("progress-bytes");
  }

  public setProgress(percent: number, status?: string, bytesText?: string): void {
    const clamped = Math.max(0, Math.min(100, Math.round(percent)));
    if (this.fillEl) this.fillEl.style.width = `${clamped}%`;
    if (this.percentEl) this.percentEl.textContent = `${clamped}%`;
    if (status && this.statusEl) this.statusEl.textContent = status;
    if (bytesText && this.bytesEl) this.bytesEl.textContent = bytesText;
  }

  public hide(): void {
    if (this.overlayEl) {
      this.overlayEl.classList.add("hidden");
      setTimeout(() => {
        if (this.overlayEl) this.overlayEl.style.display = "none";
      }, 500);
    }
  }

  public showError(message: string): void {
    if (this.statusEl) {
      this.statusEl.innerHTML = `<span style="color: #ef4444; font-weight: 600;">Error: ${message}</span>`;
    }
    if (this.bytesEl) {
      this.bytesEl.innerHTML = `<button style="background: #3b82f6; border: none; color: #fff; padding: 4px 12px; border-radius: 4px; cursor: pointer;" onclick="location.reload()">Retry</button>`;
    }
  }
}
