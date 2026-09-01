/**
 * Premium Web Audio API Sound Synthesizer for ApplyFlow Chat.
 * Generates an Apple-style soft, crystal-clear message pop / chime
 * without requiring any external audio files or assets.
 */

class AudioChimeService {
  constructor() {
    this.audioCtx = null;
    this.isMuted = false;
  }

  _getAudioContext() {
    if (typeof window === 'undefined') return null;
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume().catch(() => {});
    }
    return this.audioCtx;
  }

  /**
   * Plays a subtle, delightful dual-tone pop chime on incoming chat message.
   */
  playMessagePop() {
    if (this.isMuted) return;

    try {
      const ctx = this._getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;

      // Primary tone
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();

      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(587.33, now); // D5
      osc1.frequency.exponentialRampToValueAtTime(880.0, now + 0.08); // A5

      gain1.gain.setValueAtTime(0.001, now);
      gain1.gain.linearRampToValueAtTime(0.18, now + 0.02);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

      osc1.connect(gain1);
      gain1.connect(ctx.destination);

      osc1.start(now);
      osc1.stop(now + 0.2);

      // Harmonious second chime
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();

      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(880.0, now + 0.06); // A5
      osc2.frequency.exponentialRampToValueAtTime(1174.66, now + 0.16); // D6

      gain2.gain.setValueAtTime(0.001, now + 0.06);
      gain2.gain.linearRampToValueAtTime(0.14, now + 0.08);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.26);

      osc2.connect(gain2);
      gain2.connect(ctx.destination);

      osc2.start(now + 0.06);
      osc2.stop(now + 0.28);
    } catch {
      // Audio playback quiet fallback
    }
  }

  setMuted(muted) {
    this.isMuted = Boolean(muted);
  }
}

export const audioChime = new AudioChimeService();
export default audioChime;
