#!/usr/bin/env python3
"""[courseware-video toolkit] Helper library for score_v4.py (the current engine). The main() below is an earlier,
superseded score version kept for reference only.

03a Stacks - score v3: ONE theme, developed (not stitched), and a drop built the way the code-generated refs build it.

  .venv/bin/python score_v3.py --stems ../out/03a_stems_v2.2 [--outdir build_03a_v3]

What changed vs v2 (see DIAGNOSIS_v2_vs_refs.md):
  * one harmonic loop for the whole film, D minor, 2 bars per chord: Dm(add9) Bb(maj7) Gm7 C(add9); the theme cadence
    swaps the last chord for Asus4-A (dominant) so the drop can land on the tonic.
  * one 8-bar theme built from one rhythmic cell  | long note . . step | short, leap, rise, rise |  - the three-note
    pickup (A4 D5 E5 / F4 Bb4 C5 / D5 G5 A5) always rises into the 3rd of the next chord. It is derived from our own
    Theme A 'Starlit Proof' head (A4 D5 E5 F5).  Used: half statement in the open; call (bell) / response (piano) at
    chapter heads; full statement in the last 8 bars of the build; full statement at the climax (the pickup runs
    THROUGH the drop: E5 -> F5 lands on the reveal downbeat); recap; the cell in D MAJOR (F#5) as the final cadence.
  * drop = ref recipe: groove peaks (4-on-floor, 2&4 snare, rolling 8th bass, 16th arps), snare roll over the last
    2 bars, kick / bass / hats / arps OUT for the last bar (dip), noise riser 4 s + reversed tonic-chord swell that
    stops dead on the cut, then impact + sub + a tonic chord hit in the pad's own timbre, everything back in.
  * transitions: in-key reversed-pad swells into chapters instead of noise risers (kinetic-reel lesson).
Shares voices / SFX / mixer with score_v2.py.
"""
import argparse, json, os, sys, tempfile, shutil
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.ndimage import uniform_filter1d
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import dsp, theory as th
import score_v2 as V
from score_v2 import kick, hat, snare, bell, sub_note, pluck_note, put, sfx_sound, _push, st_loud, event_loud, \
    render_piano, norm_active, master, duck_env, PENTA, SFX_REL
SR = dsp.SR
BPM, BEAT, BAR = 120, 0.5, 2.0
rng = np.random.default_rng(11)

LOOP = ["Dmadd9", "Dmadd9", "Bbmaj7", "Bbmaj7", "Gm7", "Gm7", "Cadd9", "Cadd9"]
THEME_PROG = ["Dmadd9", "Dmadd9", "Bbmaj7", "Bbmaj7", "Gm7", "Gm7", "Asus4", "A"]
# the theme: 8 bars, 4 beats each (beat = 0.5 s). Even bars end with the 3-note pickup into the next phrase.
PICKUP = "r:1 A4:1 D5:1 E5:1"
T = ["F5:3 E5:1", "D5:1 F4:1 Bb4:1 C5:1",
     "D5:3 C5:1", "Bb4:1 D5:1 G5:1 A5:1",
     "Bb5:3 A5:1", "G5:1 E5:1 F5:1 G5:1",
     "A5:3 G5:1", "E5:1 A4:1 D5:1 E5:1"]
CLIMAX_RECAP = ["Dmadd9", "Dmadd9", "Bbmaj7", "Bbmaj7",                 # climax: theme bars 1-4
                "Gm7", "Gm7", "Cadd9", "Cadd9", "Dmadd9", "Dmadd9", "Bbmaj7", "Bbmaj7", "A",   # recap
                "Dadd9", "Dadd9", "Dadd9", "Dadd9", "Dadd9", "Dadd9", "Dadd9"]                # end (Picardy)
CR_MEL = T[0:4] + T[4:8] + T[0:3] + ["Bb4:3 r:1", "C#5:1 A4:1 D5:1 E5:1", "F#5:3 E5:1", "D5:4", "r:4", "A4:2 D5:2"]

# style: intensity (start,end), sub, kick, hat, snare, arp, arp cutoff, call-response at head
STYLE = {
    "open":   dict(I=(0.05, 0.12), sub="hold", kick="", hat="", arp="", cut=(900, 900)),
    "calm":   dict(I=(0.28, 0.29), sub="hold", kick="", hat="", arp="8s", cut=(2300, 2500), call=1),
    "pulse":  dict(I=(0.35, 0.38), sub="pulse", kick="1", hat="", arp="8s", cut=(2000, 2300), call=2),
    "lift":   dict(I=(0.48, 0.50), sub="pulse", kick="1", hat="off", arp="8", cut=(2800, 3000), call=1),
    "calm2":  dict(I=(0.30, 0.31), sub="hold", kick="", hat="", arp="8s", cut=(2300, 2500), call=1),
    "code":   dict(I=(0.38, 0.42), sub="pulse", kick="1", hat="off", arp="8s", cut=(2100, 2400), call=2),
    "code2":  dict(I=(0.44, 0.48), sub="pulse", kick="13", hat="off", arp="8", cut=(2400, 2700), call=2),
    "build":  dict(I=(0.48, 0.60), cut=(2600, 4600)),
    "climax": dict(I=(1.00, 0.97), sub="8th", kick="4", hat="16", snare="24", arp="16", cut=(5200, 5200)),
    "recap":  dict(I=(0.40, 0.28), sub="hold", kick="", hat="", arp="8s", cut=(2000, 1600)),
    "end":    dict(I=(0.22, 0.05), sub="hold", kick="", hat="", arp="", cut=(900, 700)),
}


def build_layers(k, B):
    """build section: layer windows by bar index (like the ref's KICK_W/HAT_W/ARP_W lists)."""
    if k == B - 1:                                     # the dropout bar: only pad, melody pickup, roll, swell
        return dict(sub="", kick="", hat="", snare="", arp="")
    if k < 4:  return dict(sub="pulse", kick="13", hat="off", snare="", arp="8")
    if k < 12: return dict(sub="pulse", kick="4", hat="off", snare="", arp="8")
    if k < B - 8: return dict(sub="8th", kick="4", hat="8", snare="", arp="16")
    return dict(sub="8th", kick="4", hat="16" if k >= B - 4 else "8", snare="24", arp="16")


def chord_at(secs, t):
    for s in secs:
        if s["start"] <= t < s["end"]:
            k = int((t - s["start"] + 1e-6) // BAR)
            st = s["style"]
            if st == "open":
                return ("Dmadd9" if k < 4 else "Bbmaj7"), s, k
            if st == "build":
                B = s["bars"]
                return (THEME_PROG[k - (B - 8)] if k >= B - 8 else LOOP[k % 8]), s, k
            if st in ("climax", "recap", "end"):
                off = {"climax": 0, "recap": None, "end": None}
                base = cr_offset(secs, st)
                return CLIMAX_RECAP[min(base + k, len(CLIMAX_RECAP) - 1)], s, k
            return LOOP[k % 8], s, k
    return "Dadd9", secs[-1], 0


def cr_offset(secs, st):
    S = {s["style"]: s for s in secs}
    if st == "climax": return 0
    if st == "recap": return S["climax"]["bars"]
    return S["climax"]["bars"] + S["recap"]["bars"]


def intensity(s, t):
    a, b = STYLE[s["style"]]["I"]
    x = np.clip((t - s["start"]) / max(1e-3, s["end"] - s["start"]), 0, 1)
    if s["style"] == "build":
        x = x ** 1.3
    return a + (b - a) * x


def supersaw_hit(ms, d=3.5, f0=5200, f1=900):
    """tonic chord hit in the pad's own timbre (detuned saws) with a closing low-pass - not a foreign brass."""
    n = int(d * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for m in ms:
        for c in (-8, -3, 3, 8):
            y += dsp.saw(dsp.mtof(m) * 2 ** (c / 1200), n, rng.random())
    y /= 4 * len(ms)
    # time-varying LP: blend two filtered copies
    a = dsp.butter(y, "lowpass", f0, 2); b = dsp.butter(y, "lowpass", f1, 2)
    k = np.exp(-t * 2.2)
    return (a * k + b * (1 - k)) * np.minimum(1, t / 0.006) * np.exp(-t * 0.55)


def swell(ms, length):
    """reversed pad: grows, then stops dead on the cut (in-key transition)."""
    n = int(length * SR); t = np.arange(n) / SR; q = t / length
    y = sum(sum(np.sin(2 * np.pi * dsp.mtof(m) * h * (1 + 0.002 * i) * t + h) / (h * h) for h in (1, 2, 3)) for i, m in enumerate(ms))
    y = y / len(ms) * q ** 2.6
    y[-int(0.012 * SR):] *= np.linspace(1, 0, int(0.012 * SR))
    return y


def build_plan(tl, phi):
    secs, thin, reveal = V.build_plan(tl, phi)
    return secs, thin, reveal


def build(tl, phi):
    total = tl["duration"]
    n = int(round(total * SR))
    secs, thin, reveal = build_plan(tl, phi)
    S = {s["style"]: s for s in secs}
    meter = pyln.Meter(SR)
    Bz = {k: np.zeros((n, 2), np.float32) for k in ["sub", "kick", "hat", "snare", "arp", "bell", "stab", "swell"]}
    piano, kicks, pad_events = [], [], []
    beats = [phi + k * BEAT for k in range(int(np.floor(-phi / BEAT)), int((total - phi) / BEAT) + 1)]
    in_thin = lambda t: any(a <= t < b for a, b in thin)
    bar_t = [phi + k * BAR for k in range(-1, int((total - phi) / BAR) + 2)]
    prev_v = None

    def layers(s, k):
        if s["style"] == "build":
            return build_layers(k, s["bars"])
        st = STYLE[s["style"]]
        return dict(sub=st.get("sub", ""), kick=st.get("kick", ""), hat=st.get("hat", ""), snare=st.get("snare", ""), arp=st.get("arp", ""))

    # ---- per bar: pad + sub
    for bt in bar_t:
        if bt >= total:
            break
        c, s, k = chord_at(secs, max(0, bt) + 0.01)
        I = intensity(s, max(bt, 0))
        _, pcs, bpc = th.chord(c)
        v = th.voice(pcs, 53, 74, 4, prev_v); prev_v = v
        for p in v + [th.in_range(bpc, 45, 56)[0]]:
            pad_events.append((p, max(0, bt), bt + BAR + 0.05, 0.6 + 0.4 * I))
        root = th.in_range(bpc, 33, 44)[0]
        mode = layers(s, k)["sub"]
        if mode == "hold" or (mode and in_thin(bt + 0.1)):
            put(Bz["sub"], sub_note(root, BAR), bt, 0.8)
        elif mode == "pulse":
            put(Bz["sub"], sub_note(root, 0.9), bt, 1.0); put(Bz["sub"], sub_note(root, 0.7), bt + 0.75, 0.7)
            put(Bz["sub"], sub_note(root, 0.4), bt + 1.5, 0.6)
        elif mode == "8th":      # rolling 8ths, octave on every 4th (ref drive)
            for j in range(8):
                put(Bz["sub"], sub_note(root + (12 if j % 4 == 3 else 0), 0.22), bt + j * 0.25, 0.9 if j % 2 == 0 else 0.65)
    pad_events.sort(key=lambda e: (e[0], e[1]))
    merged = []
    for e in pad_events:
        if merged and merged[-1][0] == e[0] and e[1] <= merged[-1][2] + 0.01:
            merged[-1] = (e[0], merged[-1][1], e[2], max(merged[-1][3], e[3]))
        else:
            merged.append(e)
    raw = dsp.supersaw_pad(merged, n, rng, detune_cents=(-7, -2, 3, 8), attack=1.2, release=2.0)
    grid = np.arange(0, total, 0.05)
    iv = []
    for t in grid:
        _, s, _ = chord_at(secs, t)
        iv.append(intensity(s, t))
    Ivec = np.interp(np.arange(n) / SR, grid, uniform_filter1d(np.array(iv), 20)).astype(np.float32)
    kk = Ivec[:, None] ** 1.2
    pad = dsp.butter(raw, "lowpass", 650, 2) * (1 - kk) + dsp.butter(raw, "lowpass", 4200, 2) * kk

    # ---- per beat: drums + arps
    arp_pat = [0, 2, 1, 3, 2, 1, 3, 2]
    sparse = [1, 0, 1, 1, 0, 1, 0, 1]
    prev_a = None
    for bi, bt in enumerate(beats):
        if bt < 0 or bt >= total - 1.0:
            continue
        c, s, k = chord_at(secs, bt + 0.01)
        L = layers(s, k)
        st = STYLE[s["style"]]
        x = (bt - s["start"]) / max(1e-3, s["end"] - s["start"])
        I = intensity(s, bt)
        bib = int(round(((bt - phi) % BAR) / BEAT)) % 4
        th_ = in_thin(bt) and not (s["style"] == "build")      # build: the dropout bar is designed explicitly
        if s["style"] == "climax" and bt < s["start"] + 0.01:
            th_ = False
        if not th_ and L["kick"] and (bib == 0 or (L["kick"] == "13" and bib == 2) or L["kick"] == "4"):
            put(Bz["kick"], kick(), bt, 1.0 if bib == 0 else 0.82); kicks.append(bt)
        if not th_ and L["hat"]:
            put(Bz["hat"], hat(1.0, open_=(bib == 3 and L["hat"] != "off")), bt + 0.25, 1.0, 0.3)
            if L["hat"] in ("8", "16"):
                put(Bz["hat"], hat(), bt, 0.5, -0.3)
            if L["hat"] == "16":
                put(Bz["hat"], hat(), bt + 0.125, 0.35, 0.15); put(Bz["hat"], hat(), bt + 0.375, 0.35, -0.15)
        if not th_ and L["snare"] == "24" and bib in (1, 3):
            put(Bz["snare"], snare(), bt, 1.0)
        am = L["arp"]
        if am:
            _, pcs, _ = th.chord(c)
            v = sorted(th.voice(pcs, 62, 79, 4, prev_a, avoid_low_thirds=False)); prev_a = v
            a, b_ = st["cut"]; cut = a + (b_ - a) * np.clip(x, 0, 1)
            sub = 4 if am == "16" else 2
            for j in range(sub):
                tj = bt + j * BEAT / sub
                if in_thin(tj) and s["style"] != "build":
                    continue
                step = bi * sub + j
                if am == "8s" and not sparse[step % 8]:
                    continue
                m = v[arp_pat[step % 8]] + (12 if am == "16" and (step // 8) % 2 else 0)
                g = (0.55 + 0.45 * I) * (1.0 if j == 0 else 0.8)
                pan = 0.35 * np.sin(step * 0.7)
                y = pluck_note(m, cut, g)
                put(Bz["arp"], y, tj, 1.0, pan); put(Bz["arp"], y, tj + 0.375, 0.28, -pan)

    # ---- build: snare roll over the last 2 bars, swell + riser into the reveal
    b = S["build"]; cl = S["climax"]
    roll0 = cl["start"] - 2 * BAR
    t = roll0; i = 0
    while t < cl["start"] - 0.12:
        p = (t - roll0) / (2 * BAR)
        step = 0.25 if p < 0.25 else 0.125 if p < 0.6 else 0.0625
        put(Bz["snare"], snare(0.25 + 0.75 * p ** 1.5), t, 1.0, 0.15 * np.sin(i)); t += step; i += 1
    put(Bz["swell"], swell([50, 57, 62, 65, 69], 2.0), cl["start"] - 2.0, 1.0)
    # chapter swells (in-key, into the Dm that starts every chapter section)
    for s in secs[1:]:
        if s["style"] in ("calm", "pulse", "lift", "calm2", "code", "code2", "build", "recap"):
            put(Bz["swell"], swell([50, 57, 62, 65], 1.4), s["cut"] - 1.4, 0.35)

    # ---- melody: piano (Salamander) + bell shadow, one register A4..Bb5
    def mel(bars, t0, octave=0, vel=58, bell_amp=0.0, piano_on=True, oct_double=False):
        for i, bar in enumerate(bars):
            for nm, b0, d in th.parse_bar(bar, 4):
                if nm == "r":
                    continue
                p = th.note(nm) + octave
                ts = t0 + i * BAR + b0 * BEAT; te = ts + d * BEAT
                if piano_on:
                    piano.append((p, ts + rng.normal(0, 0.005), te + 0.08, vel + rng.normal(0, 3)))
                    if oct_double:
                        piano.append((p - 12, ts + rng.normal(0, 0.005), te + 0.08, vel - 14 + rng.normal(0, 3)))
                if bell_amp:
                    put(Bz["bell"], bell(p + 12 if oct_double else p, 2.2, bell_amp), ts, 1.0, 0.2 * np.sin(p))
    o = S["open"]
    mel([PICKUP] + T[0:3] + ["Bb4:4"], o["start"] + BAR, 0, vel=50, bell_amp=0.2)   # half statement (bars 2-6)
    for s in secs[1:]:
        call = STYLE[s["style"]].get("call")
        if not call:
            continue
        mel([PICKUP, T[0]], s["start"] - BAR, 0, vel=0, bell_amp=0.75, piano_on=False)  # call: bell, pickup through the cut
        if call == 2:
            mel([T[2]], s["start"] + 2 * BAR, 0, vel=46)                                  # response: piano, over Bb
    B = b["bars"]
    for k in range(8, B - 8, 8):                                                          # build: call / response
        mel([PICKUP, T[0]], b["start"] + (k - 1) * BAR, 0, vel=0, bell_amp=0.7, piano_on=False)
        mel([T[2]], b["start"] + (k + 2) * BAR, 0, vel=52)
    tb = b["start"] + (B - 8) * BAR
    mel([PICKUP], tb - BAR, 0, vel=60, bell_amp=0.6)
    mel(T, tb, 0, vel=62, bell_amp=0.6)                                                    # full theme, last 8 bars
    # climax -> recap -> end: one continuous statement; the pickup in the dropout bar crosses the drop
    mel(CR_MEL[:4], cl["start"], 0, vel=92, bell_amp=0.55, oct_double=True)
    rc = S["recap"]
    mel(CR_MEL[4:13], rc["start"], 0, vel=56, bell_amp=0.18)
    e = S["end"]
    mel(CR_MEL[13:], e["start"], 0, vel=50, bell_amp=0.25)
    # piano LH: roots at section heads; recap / end comping
    for s in secs[1:]:
        c, _, _ = chord_at(secs, s["start"] + 0.01)
        _, pcs, bpc = th.chord(c)
        r = th.in_range(bpc, 38, 49)[0]
        piano += [(r, s["start"], s["start"] + 3.5, 50), (r + 7, s["start"] + 0.02, s["start"] + 3.5, 42)]
    for bt in bar_t:
        if rc["start"] <= bt < total - 1:
            c, _, _ = chord_at(secs, bt + 0.01)
            _, pcs, bpc = th.chord(c)
            v = th.voice(pcs[:3], 50, 64, 3)
            piano += [(th.in_range(bpc, 38, 49)[0], bt, bt + BAR + 0.3, 44)] + [(p, bt + BEAT * (i + 1), bt + BAR + 0.3, 34) for i, p in enumerate(v)]
    # the drop: tonic chord hit (pad timbre) + low piano octave
    put(Bz["stab"], supersaw_hit([38, 45, 50, 53, 57, 62, 65]), cl["start"], 1.0)
    piano += [(26, cl["start"], cl["start"] + 3, 96), (38, cl["start"], cl["start"] + 3, 90)]
    with tempfile.TemporaryDirectory() as tmp:
        P = render_piano(piano, n, tmp)

    # ---- sidechain
    duck = np.ones(n, np.float32)
    Ld = int(0.32 * SR); shape = 1 - 0.4 * np.exp(-np.arange(Ld) / (0.1 * SR))
    for t in kicks:
        i = int(t * SR); m = min(Ld, n - i)
        if m > 0: duck[i:i + m] = np.minimum(duck[i:i + m], shape[:m])
    lv = dict(pad=(-25, 0.35), sub=(-23, 0.0), arp=(-31, 0.30), bell=(-31, 0.5), piano=(-21.5, 0.33), stab=(-26, 0.45), swell=(-30, 0.3))
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
    add(pad * duck[:, None], "pad", width=1.12, hp=90)
    add(dsp.butter(Bz["sub"], "lowpass", 260, 2) * duck[:, None], "sub", hp=28)
    add(Bz["arp"] * duck[:, None], "arp", hp=200)
    add(Bz["bell"], "bell", hp=300, lp=9000)
    add(P, "piano", hp=45)
    add(Bz["stab"], None, peak=-8, send=0.45)
    add(Bz["swell"], None, peak=-14, send=0.3)
    add(Bz["kick"], None, peak=-8.5, send=0.04)
    add(Bz["hat"], None, peak=-25, send=0.12)
    add(Bz["snare"], None, peak=-17, send=0.3)
    ir = dsp.make_ir(rt60=2.8, predelay=0.025, bright=0.35)
    ir = 0.55 * ir + 0.45 * ir.mean(1, keepdims=True)
    w = dsp.butter(dsp.butter(dsp.convolve(verb, ir), "highpass", 220, 2), "lowpass", 7000, 2)
    mus = mus + 0.5 * w
    # ---- macro dynamics: quiet open, chapter lifts, explicit dip in the dropout bar, climax on top
    gdb = -9.0 * (1 - Ivec)
    tvec = np.arange(n) / SR
    for a, b_ in thin:
        if abs(b_ - cl["start"]) < 1.5:
            continue
        gdb -= 2.0 * ((tvec > a) & (tvec < b_))
    gdb -= 3.5 * (tvec < o["end"] - 0.5)
    gdb += 3.5 * ((tvec >= cl["start"]) & (tvec < cl["end"] - 1.0))                        # climax on top
    gdb -= 2.5 * ((tvec > cl["start"] - BAR + 0.1) & (tvec < cl["start"] - 0.05))     # dropout dip (ref: -4 dB)
    gdb = uniform_filter1d(gdb[::240], 30)
    mus *= np.interp(np.arange(n), np.arange(len(gdb)) * 240, dsp.db(gdb)).astype(np.float32)[:, None]
    mus = dsp.butter(mus, "highpass", 28, 2)
    mus = dsp.eq(mus, "peak", 320, -1.5, 0.8)
    mus = dsp.eq(mus, "lowshelf", 110, -1.0)
    mus = dsp.eq(mus, "highshelf", 4500, 2.5)
    fo = int(3.0 * SR); mus[-fo:] *= (np.linspace(1, 0, fo) ** 2)[:, None]
    mus *= dsp.db(-16 - meter.integrated_loudness(mus))

    # ---- SFX: timeline cues + structural hits (impacts soft except the reveal; no noise risers on ordinary cuts)
    mloud = st_loud(mus)
    fx = []
    push_i = pop_i = 0; last_ch = None
    for ev in tl["sfx"]:
        chn = max([c["num"] for c in tl["chapters"] if c["t"] <= ev["t"] + 0.01] or [0])
        if chn != last_ch:
            push_i = pop_i = 0; last_ch = chn
        nm = ev["name"]; g0 = ev.get("gain", 0)
        if nm == "push":
            x = _push(PENTA[min(push_i, len(PENTA) - 1)]); push_i += 1
        elif nm == "pop":
            x = sfx_sound("pop", pop_i=pop_i); pop_i += 1
        else:
            x = sfx_sound(nm)
        if nm == "whoosh":
            g0 -= 6
        fx.append((ev["t"], nm, x, g0))
    for s in secs[1:]:
        if s["style"] in ("end",):
            continue
        big = s["style"] == "climax"
        fx.append((s["cut"], "impact", dsp.boom(int(3 * SR), 0, 1.0, rng), 3 if big else -4))
    L_ = 2 * BAR
    fx.append((cl["start"] - L_, "riser", dsp.riser(int(L_ * SR) + 10, 0, L_, 1.0, rng), 1))
    fx.append((cl["start"], "subdrop", sfx_sound("subdrop"), 0))
    sfx = np.zeros((n, 2), np.float32); log = []
    for t, nm, x, g0 in fx:
        x = x if x.ndim == 2 else np.stack([x, x], 1)
        el = event_loud(x)
        i0 = int(max(0, t) * SR)
        ref = float(np.median(mloud[max(0, i0 - int(1.5 * SR)): i0 + int(1.5 * SR)])) if i0 < n else -30
        ref = max(ref, -30.0)
        gd = ref + SFX_REL.get(nm, -10) + g0 * 0.5 - el
        put(sfx, x, t, dsp.db(gd))
        log.append(dict(t=round(t, 2), name=nm, music_local_lufs=round(ref, 1), sfx_rel_db=SFX_REL.get(nm, -10) + g0 * 0.5))
    sfx = sfx + 0.6 * dsp.butter(dsp.convolve(sfx * 0.25, ir), "highpass", 250, 2)
    plan = dict(version="v3", bpm=BPM, phase_offset_s=phi, reveal=reveal,
                sections=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()} for s in secs],
                thin=[[round(a, 2), round(b, 2)] for a, b in thin], kicks=len(kicks), sfx=log, piano_notes=len(piano))
    return mus, sfx, plan, piano


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stems", default=os.path.join(HERE, "..", "out", "03a_stems_v2.2"))
    ap.add_argument("--grid", default=os.path.join(HERE, "grid_03a.json"))
    ap.add_argument("--outdir", default=os.path.join(HERE, "build_03a_v3"))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    tl = json.load(open(os.path.join(a.stems, "timeline.json")))
    phi = json.load(open(a.grid))["fit_current"]["phase_offset_s"]
    act = json.load(open(os.path.join(a.stems, "vo_activity.json")))
    mus, sfx, plan, piano = build(tl, phi)
    n = len(mus)
    music_alone = master(mus.copy(), -16.0, -1.5)
    sf.write(os.path.join(a.outdir, "music.wav"), music_alone, SR, subtype="PCM_24")
    sf.write(os.path.join(a.outdir, "sfx.wav"), sfx, SR, subtype="FLOAT")
    nov = master(mus + sfx)
    vop = os.path.join(a.stems, "vo.wav")
    vo, _ = sf.read(vop, dtype="float32", always_2d=True)
    vo = np.pad(vo, ((0, max(0, n - len(vo))), (0, 0)))[:n]
    if vo.shape[1] == 1:
        vo = np.repeat(vo, 2, 1)
    d = duck_env(n, act, -9.0); ds = duck_env(n, act, -3.0)
    vov = master(vo + mus * dsp.db(-2.0) * d[:, None] + sfx * ds[:, None])
    for nm, x in (("noVO", nov), ("VO", vov)):
        sf.write(os.path.join(a.outdir, f"mix_{nm}.wav"), x, SR, subtype="PCM_24")
    plan["notes_check"] = sorted({th.nname(p[0]) for p in piano})
    plan["stems"] = os.path.abspath(a.stems)
    json.dump(plan, open(os.path.join(a.outdir, "plan.json"), "w"), indent=1, default=float)
    for s in plan["sections"]:
        print(f"  {s['style']:7s} cut {s['cut']:7.2f}  music {s['start']:7.2f}-{s['end']:7.2f}  bars {s['bars']}")
    print("done", a.outdir)


if __name__ == "__main__":
    main()
