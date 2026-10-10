#!/usr/bin/env python3
"""[courseware-video toolkit] Helper library for score_v4.py (the current engine). The main() below is an earlier,
superseded score version kept for reference only.

03a Stacks - score v2: ONE continuous piece, D minor / F major family (D dorian / F lydian colour from Theme C),
120 BPM 4/4 fixed (half-time feel), timeline-driven music + SFX in one script (like the BV1hph reference's music.py).

  ../venv/bin/python score_v2.py [--timeline ../out/03a_stems/timeline.json] [--stems ../out/03a_stems] [--mux]

Fit-to-current mode: the bar grid has one fixed phase (grid_03a.json: fit_current.phase_offset_s). Section changes snap
to the nearest downbeat of that grid; impacts / risers / whooshes stay on the exact cut times; around each cut the
pulse layers thin out (breath) instead of the tempo bending.
Outputs -> build_03a_v2/: music.wav (score alone, -16 LUFS), sfx.wav, mix_noVO.wav/.m4a, mix_VO.wav/.m4a, plan.json
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf, pyloudnorm as pyln, pretty_midi
from scipy import signal
from scipy.ndimage import uniform_filter1d
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import dsp, theory as th
SR = dsp.SR
BPM, BEAT, BAR = 120, 0.5, 2.0
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import cvs_config as _C
SAL = _C.SF2          # $CVS_SF2 or $CVS_HOME/soundfonts/SalamanderGrandPiano-V3+20200602.sf2 (install.sh)
KEY_SHIFT = 0         # semitones from D; set by score_v4 for pitched SFX (chimes, error)
ALLOWED = "D E F G A Bb C B C#"     # D aeolian + B natural (dorian/lydian colour) + C# (A chord in the build tail)
rng = np.random.default_rng(3)

# ------------------------------------------------------------------ musical material
PROG = {
    "open":   [("Dm9", 4), ("G/D", 2)],
    "calm":   [("Dm9", 2), ("Bbmaj7", 2), ("Fmaj7", 2), ("Cadd9", 2)],
    "pulse":  [("Dm9", 2), ("Bbmaj7", 2), ("Fmaj7", 2), ("Cadd9", 2)],
    "lift":   [("Bbmaj7", 1), ("C", 1), ("Dm9", 2)],
    "calm2":  [("Gm9", 2), ("Bbmaj7", 2), ("Dm9", 2), ("Cadd9", 2)],
    "code":   [("Dm9", 1), ("Dm9", 1), ("Bbmaj7", 1), ("C", 1)],
    "code2":  [("Dm9", 1), ("Bbmaj7", 1), ("Fmaj7", 1), ("C", 1)],
    "build":  [("Gm9", 1), ("Bbmaj7", 1), ("Dm9", 1), ("C", 1)],
    "climax": [("F", 1), ("G/F", 1), ("Dm9", 1), ("G/D", 1)],
    "recap":  [("Bbmaj7", 1), ("F/A", 1), ("Gm7", 1), ("Dm9", 1), ("Bbmaj7", 1), ("F/A", 1), ("Gm7", 1), ("Csus4", 1), ("C", 1)],
    "end":    [("Fadd9", 8)],
}
TAIL = {"build": [("Bbmaj7", 1), ("C", 1), ("Asus4", 1), ("A", 1)]}
# style: intensity (start, end), sub mode, kick, hat, snare, arp mode, arp cutoff (start,end)
STYLE = {
    "open":   dict(I=(0.04, 0.14), sub="hold", kick="", hat="", snare="", arp="", cut=(900, 900)),
    "calm":   dict(I=(0.28, 0.30), sub="hold", kick="", hat="", snare="", arp="8s", cut=(2400, 2600)),
    "pulse":  dict(I=(0.34, 0.38), sub="pulse", kick="1", hat="", snare="", arp="8s", cut=(2000, 2200)),
    "lift":   dict(I=(0.48, 0.50), sub="pulse", kick="1", hat="off", snare="", arp="8", cut=(2800, 3000)),
    "calm2":  dict(I=(0.30, 0.32), sub="hold", kick="", hat="", snare="", arp="8s", cut=(2400, 2600)),
    "code":   dict(I=(0.38, 0.42), sub="pulse", kick="1", hat="off", snare="", arp="8s", cut=(2100, 2300)),
    "code2":  dict(I=(0.44, 0.47), sub="pulse", kick="1", hat="off", snare="", arp="8", cut=(2400, 2600)),
    "build":  dict(I=(0.48, 0.90), sub="pulse", kick="13", hat="8@0.3", snare="3@0.62", arp="8|16@0.8", cut=(2400, 4200)),
    "climax": dict(I=(1.00, 0.96), sub="8th", kick="13", hat="8", snare="3", arp="16", cut=(4500, 4500)),
    "recap":  dict(I=(0.36, 0.26), sub="hold", kick="", hat="", snare="", arp="8s", cut=(2000, 1600)),
    "end":    dict(I=(0.22, 0.05), sub="hold", kick="", hat="", snare="", arp="", cut=(900, 700)),
}
# melodies: list of bars, each "Note:beats ..." (beat = 0.5 s)
M1 = ["C5:1 F5:1 G5:2", "A5:3 G5:1", "F5:1 G5:1 C6:2", "B5:4"]                       # Theme C 'Event Horizon' head
M2 = ["D5:0.5 A4:0.5 D5:0.5 E5:0.5 F5:1 E5:0.5 D5:0.5", "F5:0.5 E5:0.5 D5:1 A4:2"]    # Theme B 'Pointer Drift' head (in D minor)
RECAP = ["F5:2 D5:1 A4:1", "C5:2 A4:2", "Bb4:1 D5:1 F5:2", "E5:4",
         "C5:1 F5:1 G5:2", "A5:3 G5:1", "F5:1 G5:1 C6:2", "F5:4", "E5:4"]
END_MEL = ["F5:4 A5:4"]


# ------------------------------------------------------------------ plan from the timeline
DEFAULT_CUES = [["start", "open"], ["ch:1", "calm"], ["ch:2", "pulse"], ["ch:3", "lift"], ["ch:4", "calm2"],
                ["ch:5", "code"], ["ch:6", "code2"], ["ch:7", "build"], ["cap:m12", "climax"], ["ch:8", "recap"],
                ["cap:e1", "end"]]       # the 'Stacks' episode cue sheet


def anchor_time(tl, a):
    """'start' | 'ch:<num>' | 'cap:<caption id>' | '<seconds>' -> time on the timeline."""
    if a == "start": return 0.0
    kind, _, v = str(a).partition(":")
    if kind == "ch":
        for c in tl["chapters"]:
            if str(c["num"]) == v: return c["t"]
        raise KeyError(f"no chapter {v} in timeline")
    if kind == "cap":
        for c in tl["captions"]:
            if c.get("id") == v: return c["t"]
        raise KeyError(f"no caption id {v} in timeline")
    return float(a)


def build_plan(tl, phi, cues=None):
    raw = [(anchor_time(tl, a), st) for a, st in (cues or DEFAULT_CUES)]
    raw[0] = (0.0, raw[0][1])
    reveal = next(t for t, st in raw if st == "climax")
    snap = lambda t: phi + round((t - phi) / BAR) * BAR
    secs = []
    for i, (t, st) in enumerate(raw):
        d = phi - BAR if i == 0 else snap(t)
        secs.append(dict(style=st, cut=t, start=d))
    for i, s in enumerate(secs):
        s["end"] = secs[i + 1]["start"] if i + 1 < len(secs) else tl["duration"] + 4
        s["bars"] = int(round((s["end"] - s["start"]) / BAR))
    thin = []   # (a, b) windows where the pulse layers breathe out
    for s in secs[1:]:
        a, b = min(s["cut"], s["start"]) - 0.9, max(s["cut"], s["start"]) + 0.05
        thin.append((a, b))
    for c in tl["captions"]:
        if c["en"].lower().startswith("pause and think"):
            thin.append((c["t"] - 0.3, c["end"] + 0.2))
    return secs, thin, reveal


def chord_at(secs, t):
    for s in secs:
        if s["start"] <= t < s["end"]:
            k = int((t - s["start"] + 1e-6) // BAR)
            tail = TAIL.get(s["style"], [])
            if tail and k >= s["bars"] - len(tail):
                seq = tail; k = k - (s["bars"] - len(tail))
            else:
                seq = PROG[s["style"]]
            flat = [c for c, n in seq for _ in range(n)]
            return flat[k % len(flat)], s
    return "Fadd9", secs[-1]


def intensity(s, t):
    a, b = STYLE[s["style"]]["I"]
    x = np.clip((t - s["start"]) / max(1e-3, s["end"] - s["start"]), 0, 1)
    if s["style"] == "build":
        x = x ** 1.5
    return a + (b - a) * x


def gate(spec, x):
    """'8|16@0.8' -> value active at progress x"""
    if not spec:
        return ""
    val = spec
    for part in spec.split("|"):
        if "@" in part:
            v, th_ = part.split("@")
            if x >= float(th_):
                val = v
        else:
            val = part
    if "@" in val:
        v, th_ = val.split("@")
        return v if x >= float(th_) else ""
    return val


# ------------------------------------------------------------------ synth voices (numpy)
def kick(amp=1.0):
    t = np.arange(int(0.45 * SR)) / SR
    f = 42 + 85 * np.exp(-t * 30)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    y += 0.08 * rng.standard_normal(len(t)) * np.exp(-t * 300)
    return np.tanh(1.3 * y) * amp


def hat(amp=1.0, open_=False):
    n = int((0.22 if open_ else 0.05) * SR); t = np.arange(n) / SR
    y = dsp.butter(rng.standard_normal(n).astype(np.float32), "bandpass", [6500, 11000], 2)
    return y * np.exp(-t * (16 if open_ else 75)) * amp


def snare(amp=1.0):   # soft clap/snare (half-time backbeat)
    n = int(0.4 * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.4
    nz = dsp.butter(rng.standard_normal(n).astype(np.float32), "bandpass", [900, 6000], 2) * np.exp(-t * 14)
    return (body + nz) * amp


def bell(m, d=2.2, amp=1.0):   # 2-op FM bell, in tune
    n = int(d * SR); t = np.arange(n) / SR
    f = dsp.mtof(m)
    idx = 2.2 * np.exp(-t * 3.5)
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t))
    y += 0.3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)
    return y * np.exp(-t * 2.4) * np.minimum(1, t / 0.002) * amp


def sub_note(m, d, amp=1.0):
    n = int((d + 0.15) * SR); t = np.arange(n) / SR
    f = dsp.mtof(m)
    y = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * dsp.saw(f, n)
    env = np.minimum(1, t / 0.01) * np.clip((d + 0.15 - t) / 0.15, 0, 1)
    return y * env * amp


def pluck_note(m, cut, amp=1.0, d=0.45):
    n = int(d * SR); t = np.arange(n) / SR
    f = dsp.mtof(m)
    y = 0.6 * dsp.saw(f, n, rng.random()) + 0.4 * dsp.saw(f * 1.003, n, rng.random()) + 0.3 * np.sin(2 * np.pi * f * t)
    y = dsp.butter(y, "lowpass", cut, 2)
    return y * np.exp(-t * 9) * np.minimum(1, t / 0.003) * amp


def stab(ms, d=5.0):   # brass-like synth chord hit for the reveal
    n = int(d * SR); t = np.arange(n) / SR
    y = sum(dsp.saw(dsp.mtof(m), n, rng.random()) + dsp.saw(dsp.mtof(m) * 1.004, n, rng.random()) for m in ms)
    y = dsp.butter(y, "lowpass", 1300, 2) * np.exp(-t * 0.5) * np.minimum(1, t / 0.01)
    return y / len(ms)


def put(bus, x, t0, gain=1.0, pan=0.0):
    i = int(round(t0 * SR))
    if x.ndim == 1:
        a = (pan + 1) * np.pi / 4
        x = np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)
    if i < 0:
        x = x[-i:]; i = 0
    if i >= len(bus):
        return
    k = min(len(x), len(bus) - i)
    bus[i:i + k] += (x[:k] * gain).astype(np.float32)


# ------------------------------------------------------------------ SFX bank (own synthesis, pitched to the key)
PENTA = [62, 65, 67, 69, 72, 74, 77, 79, 81, 84]   # D minor pentatonic D4..C6


def sfx_sound(name, push_i=0, pop_i=0):
    n = lambda d: int(d * SR)
    if name == "pop":
        m = PENTA[max(0, len(PENTA) - 3 - pop_i % 7)]
        x = pluck_note(m, 2600, 1.0, 0.4)
        t = np.arange(len(x)) / SR
        return x * (1 - 0.3 * t)
    if name in ("chime", "chime_hi", "chime_lo"):
        m = {"chime": 81, "chime_hi": 86, "chime_lo": 74}[name] + KEY_SHIFT
        a = bell(m, 2.5, 1.0); b = 0.5 * bell(m + 12, 1.5, 0.5)
        return a + np.pad(b, (0, len(a) - len(b)))
    if name in ("click", "tick", "type"):
        d = {"click": 0.06, "tick": 0.04, "type": 0.03}[name]
        t = np.arange(n(d)) / SR
        f = {"click": 2200, "tick": 3200, "type": 1700}[name]
        return (np.sin(2 * np.pi * f * t) * np.exp(-t * 90) +
                0.3 * dsp.butter(rng.standard_normal(len(t)).astype(np.float32), "bandpass", [2000, 6000], 2) * np.exp(-t * 200))
    if name == "whoosh":
        d = 0.9; N = n(d)
        x = rng.standard_normal((N, 2)).astype(np.float32)
        f, tt, Z = signal.stft(x, fs=SR, nperseg=1024, axis=0)
        fr = Z.shape[-1]; p = np.linspace(0, 1, fr)
        fc = 350 * (3000 / 350) ** (np.sin(np.pi * p) ** 1.5)
        mask = np.exp(-0.5 * (np.log2(f[:, None] / fc[None, :] + 1e-9) / 0.8) ** 2)
        _, y = signal.istft(Z * mask[:, None, :], fs=SR, nperseg=1024, time_axis=-1, freq_axis=0)
        y = np.asarray(y); y = y.T if y.shape[0] == 2 else y
        y = y[:N]; t = np.arange(len(y)) / SR
        return y * (np.sin(np.pi * t / d) ** 2)[:, None]
    if name == "error":   # intentional muted dissonance (D3 + Eb3), soft
        t = np.arange(n(0.6)) / SR
        y = (np.sin(2 * np.pi * dsp.mtof(50 + KEY_SHIFT) * t) + 0.8 * np.sin(2 * np.pi * dsp.mtof(51 + KEY_SHIFT) * t)) * np.exp(-t * 6)
        return dsp.butter(y * np.minimum(1, t / 0.01), "lowpass", 1500, 2)
    if name in ("boom", "impact"):
        return dsp.boom(n(3.0), 0.0, 1.0, rng)
    if name == "swell":
        return dsp.riser(n(3.6), 0.0, 3.5, 1.0, rng)
    if name == "subdrop":
        t = np.arange(n(2.0)) / SR
        f = 30 + 60 * np.exp(-t * 2.5)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3)
    raise KeyError(name)


# fix the odd push construction above (bell + padded pluck)
def _push(m):
    b = bell(m + 12, 0.9, 1.0) * 0.6
    p = pluck_note(m, 3000, 0.6, 0.35)
    p = np.pad(p, (0, len(b) - len(p)))
    return b + p


# loudness proxy (K-weighting approximation) per 400 ms window
def kweight(x):
    y = dsp.eq(x, "highshelf", 1500, 4.0)
    return dsp.butter(y, "highpass", 60, 2)


def st_loud(x, win=0.4):
    y = kweight(x if x.ndim == 2 else np.stack([x, x], 1))
    p = (y ** 2).sum(1)
    w = int(win * SR)
    m = uniform_filter1d(p, w)
    return -0.691 + 10 * np.log10(m + 1e-12)


def event_loud(x):
    return float(np.max(st_loud(x)))


SFX_REL = dict(impact=-3, riser=-6, whoosh=-9, push=-7, pop=-8, chime=-7, chime_hi=-9, chime_lo=-6, error=-6,
               click=-12, tick=-12, type=-14, swell=-6, boom=-4, subdrop=-4)


# ------------------------------------------------------------------ piano via FluidSynth (Salamander)
def render_piano(notes, n, tmp):
    pm = pretty_midi.PrettyMIDI(initial_tempo=BPM, resolution=960)
    ins = pretty_midi.Instrument(program=0, name="piano")
    notes = sorted(notes, key=lambda z: (z[0], z[1]))
    for i, (p, t0, t1, v) in enumerate(notes):   # no same-pitch overlaps
        if i + 1 < len(notes) and notes[i + 1][0] == p and notes[i + 1][1] < t1:
            t1 = notes[i + 1][1] - 0.01
        ins.notes.append(pretty_midi.Note(velocity=int(np.clip(v, 1, 127)), pitch=p, start=max(0, t0), end=max(t0 + 0.05, t1)))
    ins.control_changes.append(pretty_midi.ControlChange(7, 100, n / SR + 4))
    pm.instruments.append(ins)
    mid, wav = os.path.join(tmp, "p.mid"), os.path.join(tmp, "p.wav")
    pm.write(mid)
    subprocess.run(["fluidsynth", "-ni", "-q", "-R", "0", "-C", "0", "-g", "0.5", "-r", str(SR), "-O", "float", "-T", "wav",
                    "-o", "synth.dynamic-sample-loading=1", "-F", wav, SAL, mid], check=True, stdout=subprocess.DEVNULL)
    x, _ = sf.read(wav, dtype="float32", always_2d=True)
    return np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]


def norm_active(x, target_db):
    r = dsp.active_rms_db(x)
    return x * dsp.db(target_db - r) if r > -110 else x


# ------------------------------------------------------------------ main build
def build(tl, phi, vo_act):
    total = tl["duration"]
    n = int(round(total * SR))
    secs, thin, reveal = build_plan(tl, phi)
    meter = pyln.Meter(SR)
    B = {k: np.zeros((n, 2), np.float32) for k in ["pad", "sub", "kick", "hat", "snare", "arp", "bell", "stab", "verb", "fx", "fxverb"]}
    piano = []
    kicks = []
    beats = [phi + k * BEAT for k in range(int(np.floor(-phi / BEAT)), int((total - phi) / BEAT) + 1)]
    in_thin = lambda t: any(a <= t < b for a, b in thin)
    prev_v = None
    pad_events = []
    # ---- per bar: pad, piano LH at section heads
    bar_t = [phi + k * BAR for k in range(-1, int((total - phi) / BAR) + 2)]
    for bt in bar_t:
        if bt >= total:
            break
        c, s = chord_at(secs, max(0, bt) + 0.01)
        I = intensity(s, max(bt, 0))
        _, pcs, bpc = th.chord(c)
        v = th.voice(pcs, 53, 74, 4, prev_v); prev_v = v
        for p in v + [th.in_range(bpc, 45, 56)[0]]:
            pad_events.append((p, max(0, bt), bt + BAR + 0.05, 0.6 + 0.4 * I))
        # sub bass
        root = th.in_range(bpc, 33, 44)[0]
        mode = STYLE[s["style"]]["sub"]
        if mode == "hold" or in_thin(bt + 0.1):
            put(B["sub"], sub_note(root, BAR), bt, 0.8)
        elif mode == "pulse":     # 1 and the 'and' of 2 (half-time feel)
            put(B["sub"], sub_note(root, 0.9), bt, 1.0); put(B["sub"], sub_note(root, 0.7), bt + 0.75, 0.7)
            put(B["sub"], sub_note(root, 0.4), bt + 1.5, 0.6)
        else:                     # 8ths
            for k in range(8):
                put(B["sub"], sub_note(root + (12 if k % 4 == 3 else 0), 0.22), bt + k * 0.25, 0.85 if k % 2 == 0 else 0.6)
    # merge repeated pad notes (ties) so the pad sustains instead of re-attacking every bar
    pad_events.sort(key=lambda e: (e[0], e[1]))
    merged = []
    for e in pad_events:
        if merged and merged[-1][0] == e[0] and e[1] <= merged[-1][2] + 0.01:
            merged[-1] = (e[0], merged[-1][1], e[2], max(merged[-1][3], e[3]))
        else:
            merged.append(e)
    raw = dsp.supersaw_pad(merged, n, rng, detune_cents=(-7, -2, 3, 8), attack=1.2, release=2.0)
    Ivec = np.zeros(n, np.float32); Cvec = np.zeros(n, np.float32)
    grid = np.arange(0, total, 0.05)
    iv, cv = [], []
    for t in grid:
        c, s = chord_at(secs, t)
        iv.append(intensity(s, t))
        a, b = STYLE[s["style"]]["cut"]
        x = (t - s["start"]) / max(1e-3, s["end"] - s["start"])
        cv.append(a + (b - a) * np.clip(x, 0, 1))
    Ivec = np.interp(np.arange(n) / SR, grid, uniform_filter1d(np.array(iv), 20)).astype(np.float32)
    k = Ivec[:, None] ** 1.2
    B["pad"] = dsp.butter(raw, "lowpass", 650, 2) * (1 - k) + dsp.butter(raw, "lowpass", 3800, 2) * k
    # ---- per beat / 8th / 16th: drums + arps
    arp_pat = [0, 2, 1, 3, 2, 1, 3, 2]
    sparse = [1, 0, 1, 1, 0, 1, 0, 1]
    prev_a = None
    for bi, bt in enumerate(beats):
        if bt < 0 or bt >= total - 1.0:
            continue
        c, s = chord_at(secs, bt + 0.01)
        st = STYLE[s["style"]]
        x = (bt - s["start"]) / max(1e-3, s["end"] - s["start"])
        I = intensity(s, bt)
        beat_in_bar = int(round(((bt - phi) % BAR) / BEAT)) % 4
        thin_now = in_thin(bt)
        kk = gate(st["kick"], x)
        if not thin_now and kk and ((beat_in_bar == 0) or (kk == "13" and beat_in_bar == 2)):
            put(B["kick"], kick(), bt, 1.0 if beat_in_bar == 0 else 0.8); kicks.append(bt)
        hh = gate(st["hat"], x)
        if not thin_now and hh:
            put(B["hat"], hat(), bt + 0.25, 1.0, 0.3)
            if hh == "8":
                put(B["hat"], hat(), bt, 0.5, -0.3)
        sn = gate(st["snare"], x)
        if not thin_now and sn and beat_in_bar == 2:
            put(B["snare"], snare(), bt, 1.0)
        am = gate(st["arp"], x)
        if am:
            _, pcs, _ = th.chord(c)
            v = sorted(th.voice(pcs, 62, 79, 4, prev_a, avoid_low_thirds=False)); prev_a = v
            a, b_ = st["cut"]; cut = a + (b_ - a) * np.clip(x, 0, 1)
            sub = 4 if am == "16" else 2
            for j in range(sub):
                tj = bt + j * BEAT / sub
                if in_thin(tj):
                    continue
                step = (bi * sub + j)
                if am == "8s" and not sparse[step % 8]:
                    continue
                m = v[arp_pat[step % 8]] + (12 if am == "16" and (step // 8) % 2 else 0)
                g = (0.55 + 0.45 * I) * (1.0 if j == 0 else 0.8)
                pan = 0.35 * np.sin(step * 0.7)
                y = pluck_note(m, cut, g)
                put(B["arp"], y, tj, 1.0, pan)
                put(B["arp"], y, tj + 0.375, 0.28, -pan)     # dotted-8th echo
    # ---- melodies (piano, bell)
    def mel(bars, t0, octave=0, vel=(58, 0), inst="piano", amp=1.0):
        for i, bar in enumerate(bars):
            for nm, b0, d in th.parse_bar(bar, 4):
                if nm == "r":
                    continue
                p = th.note(nm) + octave
                ts = t0 + i * BAR + b0 * BEAT
                te = ts + d * BEAT
                if inst == "piano":
                    piano.append((p, ts + rng.normal(0, 0.006), te + 0.1, vel[0] + rng.normal(0, 3) + 0.3 * (p - 72)))
                else:
                    put(B["bell"], bell(p, 2.2, amp), ts, 1.0, 0.2 * np.sin(p))
    S = {s["style"]: s for s in secs}
    open_s = S["open"]
    mel(M1, open_s["start"] + BAR, 0, (52, 0))                       # opening: single motif over the pad
    mel(M1, open_s["start"] + BAR, 12, (30, 0), "bell", 0.25)        # faint bell shadow
    for st_ in ("code", "code2", "build", "lift"):
        s = S[st_]
        mel(M2, s["start"], 0, inst="bell", amp=0.9)                    # Pointer motif at the code chapter heads
    b = S["build"]
    for k_ in range(4, b["bars"] - 6, 8):                                 # recurring pointer motif in the build
        mel(M2, b["start"] + k_ * BAR, 0, inst="bell", amp=0.7 + 0.3 * k_ / b["bars"])
        mel(M2, b["start"] + k_ * BAR, -12, (42 + 2 * k_ / 4, 0))
    cl = S["climax"]
    mel(M1, cl["start"], 0, (82, 0)); mel(M1, cl["start"], 12, (60, 0)); mel(M1, cl["start"], 12, inst="bell", amp=0.6)
    rc = S["recap"]
    mel(RECAP, rc["start"], 0, (54, 0))
    mel(END_MEL, S["end"]["start"], 0, (46, 0))
    # piano LH: soft roots + fifths at every section head (small lift) and through the recap/end
    for s in secs[1:]:
        c, _ = chord_at(secs, s["start"] + 0.01)
        _, pcs, bpc = th.chord(c)
        r = th.in_range(bpc, 38, 49)[0]
        piano += [(r, s["start"], s["start"] + 3.5, 50), (r + 7, s["start"] + 0.02, s["start"] + 3.5, 42)]
    for bt in bar_t:
        if rc["start"] <= bt < total - 1:
            c, _ = chord_at(secs, bt + 0.01)
            _, pcs, bpc = th.chord(c)
            v = th.voice(pcs, 50, 64, 3)
            piano += [(th.in_range(bpc, 38, 49)[0], bt, bt + BAR + 0.3, 44)] + [(p, bt + BEAT * (i + 1), bt + BAR + 0.3, 34) for i, p in enumerate(v)]
    # reveal stab (F major, brass-like) + its tail
    put(B["stab"], stab([41, 48, 53, 57, 60]), cl["start"], 1.0)
    with tempfile.TemporaryDirectory() as tmp:
        P = render_piano(piano, n, tmp)
    # ---- sidechain from kicks
    duck = np.ones(n, np.float32)
    L = int(0.32 * SR); shape = 1 - 0.32 * np.exp(-np.arange(L) / (0.09 * SR))
    for t in kicks:
        i = int(t * SR); m = min(L, n - i)
        if m > 0: duck[i:i + m] = np.minimum(duck[i:i + m], shape[:m])
    # ---- level each bus, sends
    lv = dict(pad=(-25, 0.35), sub=(-24, 0.0), arp=(-31, 0.30), bell=(-31, 0.55), piano=(-22, 0.35), stab=(-27, 0.5))
    mus = np.zeros((n, 2), np.float32); verb = np.zeros((n, 2), np.float32)
    def add(x, key, width=1.0, hp=None, lp=None, peak=None, send=0.0):
        nonlocal mus, verb
        if hp: x = dsp.butter(x, "highpass", hp, 2)
        if lp: x = dsp.butter(x, "lowpass", lp, 2)
        if width != 1.0: x = dsp.widen(x, width)
        if peak is not None:
            x = x * (dsp.db(peak) / (np.max(np.abs(x)) + 1e-9))
        else:
            x = norm_active(x, lv[key][0]); send = lv[key][1]
        mus += x; verb += x * send
    add(B["pad"] * duck[:, None], "pad", width=1.15, hp=90)
    add(dsp.butter(B["sub"], "lowpass", 260, 2) * duck[:, None], "sub", hp=28)
    add(B["arp"] * duck[:, None], "arp", hp=200)
    add(B["bell"], "bell", hp=300, lp=9000)
    add(P, "piano", hp=50)
    add(B["stab"], "stab", hp=80)
    add(B["kick"], None, peak=-9, send=0.05)
    add(B["hat"], None, peak=-26, send=0.15)
    add(B["snare"], None, peak=-19, send=0.35)
    ir = dsp.make_ir(rt60=2.8, predelay=0.025, bright=0.35)
    ir = 0.55 * ir + 0.45 * ir.mean(1, keepdims=True)          # less decorrelated -> narrower, less washy image
    w = dsp.butter(dsp.butter(dsp.convolve(verb, ir), "highpass", 220, 2), "lowpass", 7000, 2)
    mus = mus + 0.5 * w
    # ---- macro dynamics by intensity (quiet open, lift per chapter, climax), thin windows dip a little
    gdb = -7.5 * (1 - Ivec)
    tvec = np.arange(n) / SR
    for a, b_ in thin:
        gdb -= 2.0 * ((tvec > a) & (tvec < b_))
    gdb -= 3.5 * (tvec < S["open"]["end"] - 0.5)          # extra-quiet cold open (refs: -20..-24 LUFS first 10 s)
    gdb = uniform_filter1d(gdb[::240], 100)
    mus *= np.interp(np.arange(n), np.arange(len(gdb)) * 240, dsp.db(gdb)).astype(np.float32)[:, None]
    mus = dsp.butter(mus, "highpass", 28, 2)
    mus = dsp.eq(mus, "peak", 320, -1.5, 0.8)
    mus = dsp.eq(mus, "lowshelf", 110, -1.5)
    mus = dsp.eq(mus, "highshelf", 4500, 2.5)
    fo = int(3.0 * SR); mus[-fo:] *= (np.linspace(1, 0, fo) ** 2)[:, None]
    mus *= dsp.db(-16 - meter.integrated_loudness(mus))
    # ---- SFX from the timeline cues + designed impacts / risers at chapter cuts (balanced to the local music level)
    mloud = st_loud(mus)
    fx_events = []
    push_i = pop_i = 0; last_ch = None
    for e in tl["sfx"]:
        chn = max([c["num"] for c in tl["chapters"] if c["t"] <= e["t"] + 0.01] or [0])
        if chn != last_ch:
            push_i = pop_i = 0; last_ch = chn
        nm = e["name"]
        if nm == "push":
            x = _push(PENTA[min(push_i, len(PENTA) - 1)]); push_i += 1
        elif nm == "pop":
            x = sfx_sound("pop", pop_i=pop_i); pop_i += 1
        else:
            x = sfx_sound(nm)
        fx_events.append((e["t"], nm, x, e.get("gain", 0)))
    for s in secs[1:]:
        big = s["style"] in ("climax",)
        if s["style"] != "end":
            fx_events.append((s["cut"], "impact", dsp.boom(int(3 * SR), 0, 1.0, rng), 2 if big else 0))
        L_ = 8.0 if big else BAR
        fx_events.append((s["cut"] - L_, "riser", dsp.riser(int(L_ * SR) + 10, 0, L_, 1.0, rng), 2 if big else -2))
    fx_events.append((cl["start"], "subdrop", sfx_sound("subdrop"), 0))
    sfx = np.zeros((n, 2), np.float32); log = []
    for t, nm, x, g0 in fx_events:
        x = x if x.ndim == 2 else np.stack([x, x], 1)
        el = event_loud(x)
        i0 = int(max(0, t) * SR)
        ref = float(np.median(mloud[max(0, i0 - int(1.5 * SR)): i0 + int(1.5 * SR)])) if i0 < n else -30
        ref = max(ref, -30.0)          # very quiet music: keep SFX at a sane floor, not inaudible
        gdb_ = ref + SFX_REL.get(nm, -10) + g0 * 0.5 - el
        put(sfx, x, t, dsp.db(gdb_))
        log.append(dict(t=round(t, 2), name=nm, music_local_lufs=round(ref, 1), sfx_rel_db=SFX_REL.get(nm, -10) + g0 * 0.5))
    sfx_wet = dsp.butter(dsp.convolve(sfx * 0.25, ir), "highpass", 250, 2)
    sfx = sfx + 0.6 * sfx_wet
    plan = dict(bpm=BPM, phase_offset_s=phi, sections=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()} for s in secs],
                thin=[[round(a, 2), round(b, 2)] for a, b in thin], kicks=len(kicks), sfx=log, piano_notes=len(piano))
    return mus, sfx, plan, piano


def master(x, target=-16.0, tp=-1.5):
    meter = pyln.Meter(SR)
    for _ in range(3):
        x = x * dsp.db(target - meter.integrated_loudness(x))
        x = dsp.tp_limit(x, ceiling_db=tp - 0.3)
    return x


def duck_env(n, act, depth_db=-9.0, attack=0.2, release=0.8, lead=0.15):
    g = np.zeros(n, np.float32)
    for a, b in act:
        g[max(0, int((a - lead) * SR)):min(n, int((b + 0.1) * SR))] = 1
    step = SR // 1000; gs = g[::step]; out = np.zeros_like(gs); v = 0.0
    ka, kr = 1 - np.exp(-1 / (attack * 1000)), 1 - np.exp(-1 / (release * 1000))
    for i, t in enumerate(gs):
        v += (t - v) * (ka if t > v else kr); out[i] = v
    e = np.repeat(out, step)[:n]
    e = np.pad(e, (0, n - len(e)), mode="edge")
    return dsp.db(depth_db * e).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=os.path.join(HERE, "..", "out", "03a_stems", "timeline.json"))
    ap.add_argument("--stems", default=os.path.join(HERE, "..", "out", "03a_stems"))
    ap.add_argument("--grid", default=os.path.join(HERE, "grid_03a.json"))
    ap.add_argument("--outdir", default=os.path.join(HERE, "build_03a_v2"))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    tl = json.load(open(a.timeline))
    phi = json.load(open(a.grid))["fit_current"]["phase_offset_s"]
    act = json.load(open(os.path.join(a.stems, "vo_activity.json")))
    mus, sfx, plan, piano = build(tl, phi, act)
    n = len(mus)
    vo, _ = sf.read(os.path.join(a.stems, "vo.wav"), dtype="float32", always_2d=True)
    vo = np.pad(vo, ((0, max(0, n - len(vo))), (0, 0)))[:n]
    meter = pyln.Meter(SR)
    music_alone = master(mus.copy(), -16.0, -1.5)
    sf.write(os.path.join(a.outdir, "music.wav"), music_alone, SR, subtype="PCM_24")
    sf.write(os.path.join(a.outdir, "sfx.wav"), sfx, SR, subtype="FLOAT")
    # noVO: music (-16 LUFS pre-master) + balanced SFX -> -16 LUFS / TP -1.5
    nov = master(mus + sfx)
    # VO: VO at -16, music at -18 ducked -9 dB under speech (smooth), SFX -3 dB under speech
    d = duck_env(n, act, -9.0)
    ds = duck_env(n, act, -3.0)
    vom = vo + mus * dsp.db(-2.0) * d[:, None] + sfx * ds[:, None]
    vov = master(vom)
    for nm, x in (("noVO", nov), ("VO", vov)):
        sf.write(os.path.join(a.outdir, f"mix_{nm}.wav"), x, SR, subtype="PCM_24")
    plan["notes_check"] = sorted({th.nname(p[0]) for p in piano})
    json.dump(plan, open(os.path.join(a.outdir, "plan.json"), "w"), indent=1, default=float)
    print("sections:")
    for s in plan["sections"]:
        print(f"  {s['style']:7s} cut {s['cut']:7.2f}  music {s['start']:7.2f}-{s['end']:7.2f}  bars {s['bars']}")
    print("done", a.outdir)


if __name__ == "__main__":
    main()
