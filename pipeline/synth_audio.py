"""Synthesize royalty-free SFX + a music bed with numpy, so the pipeline has
audio with zero external assets. Run:  python -m pipeline.synth_audio
Overwrite any file in assets/audio/ with your own to use licensed audio instead.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio"


def _write(name: str, samples: np.ndarray) -> Path:
    samples = np.clip(samples, -1, 1)
    pcm = (samples * 32767).astype("<i2")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


def _t(dur: float) -> np.ndarray:
    return np.linspace(0, dur, int(SR * dur), endpoint=False)


def pop(dur: float = 0.13) -> np.ndarray:
    t = _t(dur)
    freq = np.linspace(760, 1500, t.size)          # quick upward chirp
    env = np.exp(-t * 34)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env
    click = (np.random.default_rng(1).standard_normal(t.size)) * np.exp(-t * 260) * 0.3
    return (body * 0.7 + click) * 0.9


def impact(dur: float = 0.75) -> np.ndarray:
    t = _t(dur)
    rng = np.random.default_rng(2)
    sub = np.sin(2 * np.pi * np.linspace(120, 42, t.size) * t) * np.exp(-t * 6)
    boom = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 10)
    noise = rng.standard_normal(t.size) * np.exp(-t * 22)
    # simple one-pole low-pass on the noise for a duller "whoomph"
    lp = np.zeros_like(noise)
    a = 0.06
    for i in range(1, noise.size):
        lp[i] = lp[i - 1] + a * (noise[i] - lp[i - 1])
    mix = sub * 0.9 + boom * 0.5 + lp * 0.8
    return mix / np.max(np.abs(mix) + 1e-9) * 0.97


def music(dur: float = 16.0, bpm: int = 120) -> np.ndarray:
    t = _t(dur)
    out = np.zeros_like(t)
    # I–V–vi–IV in A: A C#E, E G#B, F#A C#, D F#A  (one chord per bar)
    chords = [
        (220.00, 277.18, 329.63),
        (164.81, 207.65, 246.94),
        (185.00, 220.00, 277.18),
        (146.83, 185.00, 220.00),
    ]
    beat = 60.0 / bpm
    bar = beat * 4
    for bar_i in range(int(np.ceil(dur / bar))):
        chord = chords[bar_i % 4]
        b0 = bar_i * bar
        seg = (t >= b0) & (t < b0 + bar)
        lt = t[seg] - b0
        env = np.minimum(lt / 0.4, 1) * np.exp(-lt * 0.35)
        for f in chord:
            out[seg] += np.sin(2 * np.pi * f * lt) * env * 0.09
            out[seg] += np.sin(2 * np.pi * f * 2 * lt) * env * 0.03
        # soft kick on beats 1 and 3
        for k in (0, 2):
            kt = lt - k * beat
            m = (kt >= 0) & (kt < 0.2)
            out_idx = np.where(seg)[0][m]
            kk = kt[m]
            out[out_idx] += np.sin(2 * np.pi * 55 * kk) * np.exp(-kk * 30) * 0.5
    return out / np.max(np.abs(out) + 1e-9) * 0.8


def main() -> None:
    for name, sig in [
        ("pop.wav", pop()),
        ("impact.wav", impact()),
        ("music.wav", music()),
    ]:
        p = _write(name, sig)
        print(f"wrote {p}  ({sig.size / SR:.2f}s)")


if __name__ == "__main__":
    main()
