"""DSP helpers: filters, synth voices, reverb, mastering. All float32 stereo arrays shaped (N, 2)."""
import numpy as np
from scipy import signal

SR = 48000


def db(x):
    return 10 ** (x / 20.0)


# ---------------- filters ----------------
def butter(x, kind, f, order=2):
    if f is None:
        return x
    sos = signal.butter(order, f, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def _rbj(kind, f0, gain_db, q=0.707):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    cw = np.cos(w0)
    if kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "highshelf":
        sA = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    elif kind == "lowshelf":
        sA = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sA), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sA)]
        a = [(A + 1) + (A - 1) * cw + sA, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sA]
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return b, a


def eq(x, kind, f0, gain_db, q=0.707):
    b, a = _rbj(kind, f0, gain_db, q)
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


# ---------------- oscillators ----------------
def _polyblep(t, dt):
    out = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt
    out[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    x = (t[m] - 1.0) / dt
    out[m] = x * x + x + x + 1.0
    return out


def saw(freq, n, phase0=0.0):
    dt = freq / SR
    t = (phase0 + dt * np.arange(n)) % 1.0
    return (2.0 * t - 1.0 - _polyblep(t, dt)).astype(np.float32)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def env_adsr(n, a, r, sustain_n):
    """attack seconds, release seconds, sustain length (samples incl. attack); returns length n."""
    e = np.zeros(n, np.float32)
    na = max(1, int(a * SR))
    e[:min(na, n)] = np.linspace(0, 1, na, dtype=np.float32)[:min(na, n)]
    if sustain_n > na:
        e[na:min(sustain_n, n)] = 1.0
    nr = n - sustain_n
    if nr > 0:
        start = e[sustain_n - 1] if sustain_n > 0 else 0
        e[sustain_n:] = start * np.exp(-np.arange(nr) / (r * SR / 5.0))
    return e


# ---------------- synth layers ----------------
def supersaw_pad(events, total_n, rng, detune_cents=(-9, -3, 0, 4, 10), attack=1.6, release=2.8):
    """events: list of (midi, t0, t1, amp). Returns stereo raw (unfiltered) pad."""
    out = np.zeros((total_n, 2), np.float32)
    for (m, t0, t1, amp) in events:
        f = mtof(m)
        i0 = int(t0 * SR)
        sus = int((t1 - t0) * SR)
        n = sus + int(release * SR)
        n = min(n, total_n - i0)
        if n <= 0:
            continue
        e = env_adsr(n, attack, release, min(sus, n)) * amp
        for k, dc in enumerate(detune_cents):
            fr = f * 2 ** (dc / 1200)
            s = saw(fr, n, rng.random()) * e / len(detune_cents)
            p = (k / (len(detune_cents) - 1))  # spread across stereo
            out[i0:i0 + n, 0] += s * np.cos(p * np.pi / 2)
            out[i0:i0 + n, 1] += s * np.sin(p * np.pi / 2)
    return out


def drone(segments, total_n, rng):
    """segments: list of (midi_root, t0, t1, amp) - sine+octave+fifth with slow breathing, crossfaded."""
    out = np.zeros((total_n, 2), np.float32)
    for (m, t0, t1, amp) in segments:
        i0 = max(0, int((t0 - 1.5) * SR))
        i1 = min(total_n, int((t1 + 1.5) * SR))
        n = i1 - i0
        if n <= 0:
            continue
        t = np.arange(n) / SR
        f = mtof(m)
        x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t + 1.0)
             + 0.18 * np.sin(2 * np.pi * 1.5 * f * 2 * t + 2.0) + 0.08 * np.sin(2 * np.pi * 3 * f * t))
        lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t + rng.random() * 6)
        fade = np.minimum(1, np.minimum(t / 1.5, (n / SR - t) / 1.5))
        x = (x * lfo * fade * amp).astype(np.float32)
        out[i0:i1, 0] += x
        out[i0:i1, 1] += np.roll(x, 37)  # tiny decorrelation
    return out


def pluck(events, total_n, rng):
    """events (midi, t, vel01, pan). Filtered saw pluck with exp decay."""
    out = np.zeros((total_n, 2), np.float32)
    for (m, t0, v, pan) in events:
        i0 = int(t0 * SR)
        n = min(int(0.9 * SR), total_n - i0)
        if n <= 0:
            continue
        f = mtof(m)
        s = 0.6 * saw(f, n, rng.random()) + 0.4 * saw(f * 1.004, n, rng.random())
        tt = np.arange(n) / SR
        e = np.exp(-tt / 0.22) * np.minimum(1, tt / 0.004)
        s = s * e * v
        out[i0:i0 + n, 0] += s * np.cos(pan * np.pi / 2)
        out[i0:i0 + n, 1] += s * np.sin(pan * np.pi / 2)
    # two filter states blended = brighter attack, darker tail approximation
    return butter(out, "lowpass", 2400, 2)


def pingpong(x, delay_s, fb=0.35, n_taps=6, mix=0.3):
    d = int(delay_s * SR)
    out = x.copy()
    g = mix
    for k in range(1, n_taps + 1):
        ch = (k % 2)
        sh = d * k
        if sh >= len(x):
            break
        mono = 0.5 * (x[:-sh, 0] + x[:-sh, 1])
        out[sh:, ch] += mono * g
        g *= fb
    return out


def boom(total_n, t0, amp, rng):
    out = np.zeros((total_n, 2), np.float32)
    i0 = int(t0 * SR)
    n = min(int(3.0 * SR), total_n - i0)
    if n <= 0:
        return out
    t = np.arange(n) / SR
    f = 38 + 34 * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.9)
    noise = butter(rng.standard_normal(n).astype(np.float32), "lowpass", 350, 2) * np.exp(-t / 0.08) * 0.6
    x = np.tanh(1.4 * (body + noise)) * amp
    x = x * np.minimum(1, t / 0.003)
    out[i0:i0 + n, 0] += x
    out[i0:i0 + n, 1] += x
    return out


def riser(total_n, t0, t1, amp, rng, reverse_swell=False):
    """noise swell whose low-pass cutoff rises; ends at t1 (cut with short fade)."""
    out = np.zeros((total_n, 2), np.float32)
    i0, i1 = max(0, int(t0 * SR)), min(total_n, int(t1 * SR))
    n = i1 - i0
    if n < SR // 4:
        return out
    noise = rng.standard_normal((n, 2)).astype(np.float32)
    f, tt, Z = signal.stft(noise, fs=SR, nperseg=2048, axis=0)
    # Z shape (freq, ch, frames)
    frames = Z.shape[-1]
    prog = np.linspace(0, 1, frames) ** 2
    cut = 300 * (8000 / 300) ** prog
    mask = 1.0 / (1 + (f[:, None] / cut[None, :]) ** 4)
    Z = Z * mask[:, None, :]
    _, y = signal.istft(Z, fs=SR, nperseg=2048, time_axis=-1, freq_axis=0)
    y = np.asarray(y)
    if y.shape[0] == 2 and y.ndim == 2 and y.shape[1] != 2:
        y = y.T
    y = y[:n]
    if y.shape[0] < n:
        y = np.pad(y, ((0, n - y.shape[0]), (0, 0)))
    tt = np.linspace(0, 1, n)
    e = (tt ** 2.5)[:, None]
    tail = int(0.05 * SR)
    e[-tail:] *= np.linspace(1, 0, tail)[:, None]
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * e * amp
    out[i0:i1] += y.astype(np.float32)
    return out


# ---------------- reverb ----------------
def make_ir(rt60=3.5, predelay=0.025, length=None, seed=7, bright=0.5):
    rng = np.random.default_rng(seed)
    length = length or rt60 * 1.2
    n = int(length * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2), np.float32)
    bands = [(None, 400, 1.15), (400, 2000, 1.0), (2000, 6000, 0.7), (6000, None, 0.45 * (0.5 + bright))]
    for lo, hi, rtm in bands:
        nz = rng.standard_normal((n, 2)).astype(np.float32)
        if lo and hi:
            nz = butter(nz, "bandpass", [lo, hi], 2)
        elif lo:
            nz = butter(nz, "highpass", lo, 2)
        else:
            nz = butter(nz, "lowpass", hi, 2)
        tau = rt60 * rtm / 6.91
        nz *= np.exp(-t / tau)[:, None]
        ir += nz
    # smooth onset (diffuse build-up) + predelay
    ir *= np.minimum(1, t / 0.06)[:, None]
    pd = int(predelay * SR)
    ir = np.concatenate([np.zeros((pd, 2), np.float32), ir])
    # a few early reflections
    for d, g in [(0.011, 0.5), (0.019, 0.35), (0.029, 0.3), (0.041, 0.22)]:
        k = int(d * SR)
        ir[k, 0] += g * 0.3
        ir[k + 17, 1] += g * 0.3
    ir /= np.sqrt(np.sum(ir ** 2) / 2)
    return ir


def convolve(x, ir):
    y = np.zeros((len(x), 2), np.float32)
    for c in range(2):
        y[:, c] = signal.oaconvolve(x[:, c], ir[:, c], mode="full")[:len(x)]
    return y


def widen(x, amount=1.3):
    m = 0.5 * (x[:, 0] + x[:, 1])
    s = 0.5 * (x[:, 0] - x[:, 1]) * amount
    return np.stack([m + s, m - s], axis=1).astype(np.float32)


def active_rms_db(x, win=0.4, floor_db=-60):
    mono = x.mean(axis=1) if x.ndim == 2 else x
    w = int(win * SR)
    k = len(mono) // w
    if k == 0:
        return -120.0
    r = np.sqrt(np.mean(mono[:k * w].reshape(k, w) ** 2, axis=1) + 1e-12)
    rd = 20 * np.log10(r)
    top = rd.max()
    act = rd[rd > max(floor_db, top - 30)]
    if len(act) == 0:
        return -120.0
    return float(10 * np.log10(np.mean(10 ** (act / 10))))


# ---------------- mastering ----------------
def compress(x, thresh_db=-20, ratio=2.0, attack=0.03, release=0.35):
    mono = np.sqrt(np.mean(x ** 2, axis=1))
    # RMS detector via one-pole on power, decimated for speed
    hop = 64
    p = mono[: len(mono) // hop * hop].reshape(-1, hop).mean(axis=1)
    lvl = np.zeros_like(p)
    aa = np.exp(-hop / (attack * SR))
    ar = np.exp(-hop / (release * SR))
    s = 0.0
    for i, v in enumerate(p):
        c = aa if v > s else ar
        s = c * s + (1 - c) * v
        lvl[i] = s
    ldb = 20 * np.log10(lvl + 1e-9)
    over = np.maximum(0, ldb - thresh_db)
    gdb = -over * (1 - 1 / ratio)
    g = np.repeat(db(gdb), hop)
    g = np.pad(g, (0, len(x) - len(g)), mode="edge")
    return (x * g[:, None]).astype(np.float32)


def true_peak(x, os=4):
    up = signal.resample_poly(x, os, 1, axis=0)
    return float(np.max(np.abs(up)))


def tp_limit(x, ceiling_db=-1.5, lookahead=0.005, release=0.12, os=4):
    ceil = db(ceiling_db)
    up = signal.resample_poly(x, os, 1, axis=0)
    pk = np.max(np.abs(up), axis=1).reshape(-1, os).max(axis=1)[: len(x)]
    if len(pk) < len(x):
        pk = np.pad(pk, (0, len(x) - len(pk)))
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    la = int(lookahead * SR)
    from scipy.ndimage import minimum_filter1d
    need = minimum_filter1d(need, size=2 * la + 1, origin=0)
    # smooth: instant attack (already lookahead), exponential release
    g = np.empty_like(need)
    ar = np.exp(-1 / (release * SR))
    s = 1.0
    # vectorised-ish: process in python loop on decimated grid for speed
    hop = 16
    nd = need[: len(need) // hop * hop].reshape(-1, hop).min(axis=1)
    gd = np.empty_like(nd)
    arh = ar ** hop
    for i, v in enumerate(nd):
        s = v if v < s else arh * s + (1 - arh) * v
        gd[i] = s
    g = np.repeat(gd, hop)
    g = np.pad(g, (0, len(x) - len(g)), mode="edge")
    g = np.minimum(g, need)  # safety
    return (x * g[:, None]).astype(np.float32)
