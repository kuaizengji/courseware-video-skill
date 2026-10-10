"""Synthesised, deliberately soft sound-design palette (no external samples, no licence issues).
python lib/sfx.py <outdir>  -> writes 48 kHz stereo WAVs.
All files are peak-normalised to -6 dBFS; per-cue gain is applied in mix.py (base levels there)."""
import numpy as np, soundfile as sf, sys, os
from scipy.signal import butter, sosfilt
SR = 48000
rng = np.random.default_rng(7)

def env(n, a, d, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) * curve / max(d, 1e-4))
    return e

def norm(x, db=-6):
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (db / 20)
    return x

def stereo(x, width=0.0):
    if width <= 0: return np.stack([x, x], 1)
    d = int(SR * 0.006 * width)
    return np.stack([x, np.concatenate([np.zeros(d), x[:-d]])], 1)

def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)

def lp(x, f, order=2): return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)

def whoosh(dur=1.1, f0=300, f1=2600):
    n = int(SR * dur); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n); blk = 512
    for i in range(0, n, blk):
        p = i / n
        fc = f0 * (f1 / f0) ** (np.sin(np.pi * p) ** 1.5)
        seg = noise[max(0, i - 2048):i + blk]
        y = bp(seg, fc * 0.6, min(fc * 1.6, SR / 2 - 100))[-len(noise[i:i + blk]):]
        out[i:i + blk] = y
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return stereo(norm(out * e), 1.0)

def click(dur=0.09, f=2400):
    n = int(SR * dur); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * env(n, 0.001, 0.02, 5) + 0.3 * bp(rng.standard_normal(n), 2000, 6000) * env(n, 0.0005, 0.006, 5)
    return stereo(norm(lp(x, 6000)))

def chime(dur=1.6, f=880.0):
    n = int(SR * dur); t = np.arange(n) / SR
    parts = [(1, 1.0, 2.2), (2.0, 0.35, 3.0), (2.76, 0.18, 4.0), (5.4, 0.06, 6.0)]
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dc) for r, a, dc in parts)
    x *= np.minimum(1, t / 0.004)
    return stereo(norm(x), 0.6)

def push_tone():   # soft rising "pluck" + low click: element lands
    n = int(SR * 0.5); t = np.arange(n) / SR
    f = 520 * (1 + 0.15 * np.exp(-t * 30))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * np.minimum(1, t / 0.003)
    x += 0.5 * np.sin(2 * np.pi * 1040 * t) * np.exp(-t * 14)
    return stereo(norm(lp(x, 5000)), 0.3)

def pop_tone():    # soft falling pluck: element leaves
    n = int(SR * 0.5); t = np.arange(n) / SR
    f = 700 * (1 - 0.25 * (1 - np.exp(-t * 12)))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10) * np.minimum(1, t / 0.003)
    x += 0.25 * hp(rng.standard_normal(n), 3000) * np.exp(-t * 60)
    return stereo(norm(lp(x, 6000)), 0.3)

def error_tone():  # muted low dissonant pulse (crimson moments)
    n = int(SR * 0.7); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 155 * t) + 0.8 * np.sin(2 * np.pi * 164.8 * t) + 0.3 * np.sin(2 * np.pi * 310 * t)) * np.exp(-t * 5)
    x *= np.minimum(1, t / 0.01)
    return stereo(norm(lp(x, 1800)))

def tick():
    n = int(SR * 0.05); t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 3000, 7000) * np.exp(-t * 200)
    return stereo(norm(x))

def type_tick():   # console line printed
    n = int(SR * 0.07); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 80) + 0.4 * bp(rng.standard_normal(n), 1500, 5000) * np.exp(-t * 150)
    return stereo(norm(x))

def swell(dur=3.5):  # title riser: filtered noise + soft fifth pad
    n = int(SR * dur); t = np.arange(n) / SR
    e = (t / dur) ** 2 * np.minimum(1, (dur - t) / 0.3)
    nz = lp(rng.standard_normal(n), 1800) * 0.5
    pad = sum(np.sin(2 * np.pi * f * t) for f in (110, 165, 220, 330)) / 4
    return stereo(norm((nz + pad) * e), 1.0)

def boom(dur=3.0):   # soft low impact (title hit), no harsh transient
    n = int(SR * dur); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (48 + 20 * np.exp(-t * 6)) * t) * np.exp(-t * 1.6) * np.minimum(1, t / 0.02)
    x += 0.15 * lp(rng.standard_normal(n), 400) * np.exp(-t * 3)
    return stereo(norm(x), 0.5)

BANK = dict(whoosh=whoosh, click=click, chime=chime, push=push_tone, pop=pop_tone, error=error_tone,
            tick=tick, type=type_tick, swell=swell, boom=boom,
            chime_hi=lambda: chime(1.4, 1318.5), chime_lo=lambda: chime(2.2, 587.3))

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sfx")
    os.makedirs(out, exist_ok=True)
    for k, f in BANK.items():
        sf.write(os.path.join(out, k + ".wav"), f().astype(np.float32), SR)
    print("wrote", len(BANK), "sfx to", out)
