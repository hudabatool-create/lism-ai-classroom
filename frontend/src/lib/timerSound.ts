/**
 * The "time's up" sound, synthesised in the browser with Web Audio.
 *
 * Deliberately not audio files: nothing to host or cache, no CORS or CSP
 * concerns from the student iframe's origin, and it still works with no
 * network. Each option is a short pattern of sine/triangle tones chosen to
 * carry across a classroom without being alarming.
 */

export type TimerSound = "none" | "chime" | "bell" | "school_bell";

export const TIMER_SOUND_OPTIONS: { value: TimerSound; label: string }[] = [
  { value: "chime", label: "Chime (soft)" },
  { value: "bell", label: "Bell" },
  { value: "school_bell", label: "School bell" },
  { value: "none", label: "No sound" },
];

type Tone = { freq: number; start: number; duration: number; gain?: number; type?: OscillatorType };

// Frequencies are musical intervals rather than arbitrary pitches, so the
// patterns resolve pleasantly instead of sounding like an error buzzer.
const PATTERNS: Record<Exclude<TimerSound, "none">, Tone[]> = {
  // Rising major triad: C6 - E6 - G6.
  chime: [
    { freq: 1046.5, start: 0, duration: 0.5 },
    { freq: 1318.5, start: 0.16, duration: 0.5 },
    { freq: 1568.0, start: 0.32, duration: 0.7 },
  ],
  // Two strikes of a struck bell, with a harmonic above each.
  bell: [
    { freq: 880, start: 0, duration: 0.9, type: "triangle" },
    { freq: 1760, start: 0, duration: 0.6, gain: 0.25, type: "triangle" },
    { freq: 880, start: 0.55, duration: 0.9, type: "triangle" },
    { freq: 1760, start: 0.55, duration: 0.6, gain: 0.25, type: "triangle" },
  ],
  // Insistent alternating pair, the way a corridor bell reads.
  school_bell: [
    { freq: 784, start: 0, duration: 0.28, type: "square", gain: 0.14 },
    { freq: 988, start: 0.3, duration: 0.28, type: "square", gain: 0.14 },
    { freq: 784, start: 0.6, duration: 0.28, type: "square", gain: 0.14 },
    { freq: 988, start: 0.9, duration: 0.28, type: "square", gain: 0.14 },
    { freq: 784, start: 1.2, duration: 0.45, type: "square", gain: 0.14 },
  ],
};

export function playTimerSound(sound: TimerSound | undefined | null) {
  if (!sound || sound === "none") return;
  const pattern = PATTERNS[sound as Exclude<TimerSound, "none">];
  if (!pattern) return;

  try {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    const ctx = new Ctor();
    // Browsers suspend audio until the page has been interacted with. A
    // teacher has clicked Start Stage and a student has clicked Join, so by
    // the time a timer expires this normally succeeds -- but never let a
    // rejected resume throw and break the countdown UI.
    void ctx.resume?.();

    const now = ctx.currentTime;
    pattern.forEach(({ freq, start, duration, gain = 0.2, type = "sine" }) => {
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type = type;
      osc.frequency.value = freq;
      // Quick attack, exponential decay: a struck tone rather than a beep.
      env.gain.setValueAtTime(0.0001, now + start);
      env.gain.exponentialRampToValueAtTime(gain, now + start + 0.01);
      env.gain.exponentialRampToValueAtTime(0.0001, now + start + duration);
      osc.connect(env).connect(ctx.destination);
      osc.start(now + start);
      osc.stop(now + start + duration + 0.05);
    });

    const total = Math.max(...pattern.map((t) => t.start + t.duration)) + 0.3;
    window.setTimeout(() => void ctx.close?.(), total * 1000);
  } catch {
    // Audio is a nicety; the on-screen "Time's up" message is the real signal.
  }
}
