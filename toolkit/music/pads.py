"""Bed / pad timbres for the 03a structure PoC. Every bed takes the same chord list [(sym, t0, t1)] and returns a stereo
float32 buffer; the PoC normalises the bed to one loudness so the options differ only in timbre.
  X current  : supersaw, close low voicing (53-74), LP 1.1 kHz  (rejected: 太沉闷)
  A glass    : airy additive glass pad, open sus/add9 voicing D3..F5, octave shimmer, chorus
  B sweep    : warm-bright supersaw, open voicing, slow 8-s filter LFO 0.7-4.5 kHz, low-mid cut, wide
  C felt     : light string-ensemble bed + felt piano pulsing quarter notes (Salamander, soft, low-passed)
  D choir    : synthesised 'ah/oo' formant choir pad (vibrato, breath, slow vowel morph), chorus
"""
import os, tempfile
import numpy as np
from engine import dsp, theory as th
SR = dsp.SR


def open_voicing(sym):
    """root in 45..56 + 5th + octave + 9th + upper 5th + 3rd an octave up (sus/add9 colour, no low thirds)."""
    _, pcs, bpc = th.chord(sym)
    r = th.in_range(bpc, 45, 56)[0]
    third = (pcs[1] - bpc) % 12                     # 3 or 4
    return [r, r + 7, r + 12, r + 14, r + 19, r + 24 + third]


def events(chords, voicer, amp=1.0):
    ev = []
    for sym, t0, t1 in chords:
        for i, m in enumerate(voicer(sym)):
            ev.append((m, max(0.0, t0), t1 + 0.05, amp))
    ev.sort(key=lambda e: (e[0], e[1])); out = []
    for e in ev:                                       # tie repeated notes
        if out and out[-1][0] == e[0] and e[1] <= out[-1][2] + 0.01: out[-1] = (e[0], out[-1][1], e[2], e[3])
        else: out.append(e)
    return out


def env(n, a, r, sus):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a)
    rel = np.clip(1 - (t - sus / SR) / r, 0, 1)
    return np.where(np.arange(n) < sus, e, e[min(sus, n - 1)] * rel) if n else e


def chorus(x, depth_ms=3.0, base_ms=12.0, rate=0.27, mix=0.5):
    n = len(x); t = np.arange(n) / SR
    out = np.empty_like(x)
    for c, ph in ((0, 0.0), (1, np.pi)):
        d = (base_ms + depth_ms * np.sin(2 * np.pi * rate * t + ph)) * SR / 1000
        y = np.interp(np.arange(n) - d, np.arange(n), x[:, c], left=0)
        out[:, c] = (1 - mix) * x[:, c] + mix * y
    return out.astype(np.float32)


def lp_sweep(x, f_lo, f_hi, period, phase=0.0):
    """time-varying low-pass by crossfading three fixed low-passes along a slow sine LFO (log-frequency)."""
    n = len(x); t = np.arange(n) / SR
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / period + phase)          # 0..1
    fs = [f_lo, np.sqrt(f_lo * f_hi), f_hi]
    ys = [dsp.butter(x, "lowpass", f, 2) for f in fs]
    pos = lfo * 2
    w0 = np.clip(1 - pos, 0, 1); w2 = np.clip(pos - 1, 0, 1); w1 = 1 - w0 - w2
    return (ys[0] * w0[:, None] + ys[1] * w1[:, None] + ys[2] * w2[:, None]).astype(np.float32)


def air(x, rel_db=-24.0, seed=4):
    """breathy 'air' above 5 kHz that follows the bed's envelope (gives the top octave some life)."""
    from scipy.ndimage import uniform_filter1d
    e = uniform_filter1d(np.abs(x).mean(1), int(0.2 * SR))
    nz = np.random.default_rng(seed).standard_normal((len(x), 2)).astype(np.float32)
    nz = dsp.butter(dsp.butter(nz, "highpass", 5000, 2), "lowpass", 12000, 2)
    a = nz * e[:, None]
    return (a * dsp.db(rel_db + dsp.active_rms_db(x) - dsp.active_rms_db(a))).astype(np.float32)


def pan_add(out, s, i0, p):
    out[i0:i0 + len(s), 0] += s * np.cos((p + 1) * np.pi / 4)
    out[i0:i0 + len(s), 1] += s * np.sin((p + 1) * np.pi / 4)


# ---------------------------------------------------------------- X current (the rejected bed, as in poc_structure.py)
def bed_current(chords, n, rng):
    ev, prev = [], None
    for sym, t0, t1 in chords:
        _, pcs, bpc = th.chord(sym)
        v = th.voice(pcs, 53, 74, 4, prev); prev = v
        for p in v + [th.in_range(bpc, 45, 56)[0]]:
            ev.append((p, max(0, t0), t1 + 0.05, 0.8))
    ev.sort(key=lambda e: (e[0], e[1])); m = []
    for e in ev:
        if m and m[-1][0] == e[0] and e[1] <= m[-1][2] + 0.01: m[-1] = (e[0], m[-1][1], e[2], e[3])
        else: m.append(e)
    raw = dsp.supersaw_pad(m, n, rng, detune_cents=(-7, -2, 3, 8), attack=1.2, release=2.0)
    return dsp.butter(raw, "lowpass", 1100, 2)


# ---------------------------------------------------------------- A glass
def bed_glass(chords, n, rng):
    out = np.zeros((n, 2), np.float32)
    for m, t0, t1, a in events(chords, open_voicing):
        i0 = int(t0 * SR); sus = int((t1 - t0) * SR); L = min(sus + int(2.2 * SR), n - i0)
        if L <= 0: continue
        t = np.arange(L) / SR; f = dsp.mtof(m)
        e = env(L, 0.9, 2.2, sus)
        g = 1.0 if m >= 55 else 0.35                                   # keep the low root light
        for dc, p in ((-4, -0.6), (4, 0.6)):
            ff = f * 2 ** (dc / 1200); ph = rng.random() * 6.28
            s = (np.sin(2 * np.pi * ff * t + ph) + 0.32 * np.sin(4 * np.pi * ff * t + ph) + 0.1 * np.sin(6 * np.pi * ff * t)
                 + 0.06 * np.sin(2 * np.pi * 4.01 * ff * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t + ph)))
            pan_add(out, s * e * g * 0.5, i0, p * (0.3 + 0.5 * (m - 45) / 40))
        if m >= 62:                                                      # octave shimmer, slowly breathing
            sh = np.sin(2 * np.pi * 2 * f * 1.002 * t) * e * 0.22 * (0.55 + 0.45 * np.sin(2 * np.pi * 0.17 * t + rng.random() * 6))
            pan_add(out, sh, i0, rng.uniform(-0.8, 0.8))
        if m >= 69:                                                      # glassy 2-octave sparkle
            pan_add(out, np.sin(2 * np.pi * 4 * f * 0.999 * t) * e * 0.05 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.29 * t + rng.random() * 6)), i0, rng.uniform(-0.9, 0.9))
    out = chorus(out, 2.5, 14, 0.23, 0.45)
    out = out + air(out, -26)
    out = dsp.butter(out, "highpass", 170, 2)
    out = dsp.eq(out, "peak", 300, -4.5, 0.8)
    return dsp.eq(out, "highshelf", 6000, 2.5)


# ---------------------------------------------------------------- B sweep (warm-bright supersaw)
def bed_sweep(chords, n, rng):
    ev = [(m, t0, t1, a * (0.6 if m < 55 else 1.0)) for m, t0, t1, a in events(chords, open_voicing)]
    raw = dsp.supersaw_pad(ev, n, rng, detune_cents=(-12, -6, 0, 6, 12), attack=1.0, release=2.2)
    y = lp_sweep(raw, 800, 4500, 8.0)
    y = dsp.butter(y, "highpass", 160, 2)
    y = dsp.eq(y, "peak", 260, -4.0, 0.8)
    y = dsp.eq(y, "highshelf", 5000, 1.5)
    return dsp.widen(chorus(y, 2.0, 10, 0.31, 0.35), 1.35)


# ---------------------------------------------------------------- C felt piano + strings
def bed_felt(chords, n, rng, render_piano=None):
    out = np.zeros((n, 2), np.float32)
    for m, t0, t1, a in events(chords, lambda s: open_voicing(s)[:5]):  # string ensemble: low-ish, slow, light
        i0 = int(t0 * SR); sus = int((t1 - t0) * SR); L = min(sus + int(1.8 * SR), n - i0)
        if L <= 0: continue
        t = np.arange(L) / SR; e = env(L, 1.4, 1.8, sus)
        vib = 1 + 0.003 * np.sin(2 * np.pi * 5.0 * t + rng.random() * 6) * np.minimum(1, t / 1.5)
        for k, dc in enumerate((-8, 0, 8)):
            ph = np.cumsum(dsp.mtof(m) * 2 ** (dc / 1200) * vib) / SR + rng.random()
            s = (2 * (ph % 1) - 1) * e * (0.5 if m < 55 else 0.8) / 3
            pan_add(out, s, i0, (k - 1) * 0.6)
    out = dsp.butter(dsp.butter(out, "lowpass", 3600, 2), "highpass", 150, 2)
    out = dsp.eq(out, "peak", 300, -3.0, 0.9)
    notes = []                                                        # felt piano: quarter-note pulse, upper chord tones
    for sym, t0, t1 in chords:
        v = open_voicing(sym); pat = [v[3] + 12, v[4], v[5], v[4]]
        k = 0; t = t0
        while t < t1 - 1e-3:
            if t >= 0: notes.append((pat[k % 4], t, t + 0.9, 30 + (6 if k % 4 == 0 else 0)))
            t += 0.5; k += 1
    with tempfile.TemporaryDirectory() as tmp:
        P = render_piano(notes, n, tmp)
    P = dsp.butter(P, "lowpass", 5000, 2)                             # 'felt': soft hammers
    P = dsp.butter(P, "highpass", 200, 2)
    y = out * 0.8 + P * (dsp.db(dsp.active_rms_db(out) - dsp.active_rms_db(P) - 1.0))
    return y + air(y, -30)


# ---------------------------------------------------------------- D choir (formant)
VOW = {"oo": [(320, 1.0, 80), (800, 0.5, 90), (2300, 0.12, 150)], "ah": [(700, 1.0, 110), (1150, 0.7, 120), (2800, 0.25, 180)],
       "eh": [(530, 1.0, 90), (1850, 0.55, 130), (2500, 0.3, 170)]}


def bed_choir(chords, n, rng):
    src = np.zeros((n, 2), np.float32)
    for m, t0, t1, a in events(chords, lambda s: [x for x in open_voicing(s) if x >= 50]):
        i0 = int(t0 * SR); sus = int((t1 - t0) * SR); L = min(sus + int(2.0 * SR), n - i0)
        if L <= 0: continue
        t = np.arange(L) / SR; e = env(L, 1.1, 2.0, sus)
        for k in range(3):                                            # 3 singers per note
            vib = 1 + 0.0045 * np.sin(2 * np.pi * (5.0 + 0.4 * k) * t + rng.random() * 6) + 0.002 * np.convolve(rng.standard_normal(L), np.ones(2400) / 2400, "same")
            ph = np.cumsum(dsp.mtof(m) * 2 ** ((k - 1) * 6 / 1200) * vib) / SR + rng.random()
            pulse = np.where((ph % 1) < 0.35, 1.0, -0.54)            # glottal-ish pulse, brighter than a saw
            pan_add(src, pulse * e / 3, i0, rng.uniform(-0.7, 0.7))
    noise = (np.random.default_rng(3).standard_normal((n, 2)) * 0.04).astype(np.float32)
    src = src + noise * (np.abs(src).mean(1, keepdims=True) > 1e-4)  # breath only where singing
    # formant envelope in the STFT domain, vowel morphing oo -> ah -> eh -> ah over 16 s
    from scipy import signal
    f, tt, Z = signal.stft(src, fs=SR, nperseg=2048, axis=0)
    seq = ["oo", "ah", "eh", "ah"]
    pos = (tt / 4.0) % 4
    def envv(v):
        return sum(g * np.exp(-0.5 * ((f - fc) / bw) ** 2) for fc, g, bw in VOW[v]) + 0.02
    E = np.stack([envv(v) for v in seq])                             # (4, F)
    i = np.floor(pos).astype(int); fr = pos - i
    M = E[i % 4].T * (1 - fr) + E[(i + 1) % 4].T * fr               # (F, frames)
    Z = Z * M[:, None, :]
    _, y = signal.istft(Z, fs=SR, nperseg=2048, time_axis=-1, freq_axis=0)
    y = np.asarray(y); y = y.T if y.shape[0] == 2 else y
    y = np.pad(y, ((0, max(0, n - len(y))), (0, 0)))[:n].astype(np.float32)
    y = chorus(y, 3.0, 16, 0.19, 0.5)
    y = dsp.butter(y, "highpass", 180, 2)
    y = dsp.eq(y, "highshelf", 5000, 3.0)
    return y + air(y, -25)


BEDS = dict(X=("current", bed_current), A=("glass", bed_glass), B=("sweep", bed_sweep), C=("felt", bed_felt), D=("choir", bed_choir))


# ---------------------------------------------------------------- subtle variants of X (same oscillator / voicing family)
def bed_x_variant(chords, n, rng, lift=False, demud=False):
    ev, prev = [], None
    for sym, t0, t1 in chords:
        _, pcs, bpc = th.chord(sym)
        v = th.voice(pcs, 53, 74, 4, prev); prev = v
        if lift:                                   # upper notes only: top two voices up to the next chord tone
            v = sorted(v); up = []
            for m in v[2:]:
                c = [x for x in range(m + 1, m + 8) if x % 12 in pcs]
                up.append(c[0] if c else m)
            v = v[:2] + up
        for p in v + [th.in_range(bpc, 45, 56)[0]]:
            ev.append((p, max(0, t0), t1 + 0.05, 0.8))
    ev.sort(key=lambda e: (e[0], e[1])); m = []
    for e in ev:
        if m and m[-1][0] == e[0] and e[1] <= m[-1][2] + 0.01: m[-1] = (e[0], m[-1][1], e[2], e[3])
        else: m.append(e)
    raw = dsp.supersaw_pad(m, n, rng, detune_cents=(-7, -2, 3, 8), attack=1.2, release=2.0)
    y = dsp.butter(raw, "lowpass", 1800 if lift else 1100, 2)
    if demud:
        y = dsp.eq(y, "peak", 270, -3.0, 1.0)
        y = dsp.eq(y, "highshelf", 3500, 2.0)
    return y


BEDS.update(X1=("lifted", lambda c, n, r: bed_x_variant(c, n, r, lift=True)),
            X2=("lessmud", lambda c, n, r: bed_x_variant(c, n, r, demud=True)),
            X3=("lifted_lessmud", lambda c, n, r: bed_x_variant(c, n, r, lift=True, demud=True)))
