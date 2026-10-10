#!/usr/bin/env python3
"""03a Stacks - score v4: the APPROVED structure (music/REF_MUSIC_STRUCTURE.md cue sheet) over the full v2.2 timeline.
  * ONE continuous bed = pad X (supersaw, close voicing 53-74 + bass note, LP 1.1 kHz) + a soft sustained root, from 0 to
    the end, never restarted: one global chord loop on the fixed 120-BPM grid (phase 1.26 s):
    Dm(add9) Bb(maj7) Gm7 C(add9), 2 bars each; Asus4-A only at the theme cadence before the reveal and before the
    ending; D major (add9) for the end card.
  * layers switched per section (cue windows), beat-less stretches (bed + in-key SFX), near-silences (bed -7 dB, LP
    500 Hz, nothing else) before overflow and in both 'pause and think' holds, a 0.4 s dead stop before the reveal,
    v3 build (groove grows, full theme in the last 8 bars, snare roll, dropout bar) -> climax on the reveal (theme,
    Dm hit), piano recap, D-major ending.

PARAMETERISED PER EPISODE (key, progression, tempo, motif, pad, cue sheet): see scorecfg.py for the JSON format.
  python score_v4.py --stems <out/EP_stems> --grid <grid.json> --outdir <build/score> \
        [--music-config music.json] [--key "E minor"] [--bpm 100] [--pad X2] [--seed 11]
With no config/flags it reproduces the approved 'Stacks' score (D minor, 120 BPM, X2 bed).
Needs: <stems>/timeline.json + vo_activity.json + vo.wav (written by lib/post.py), grid.json (grid_03a.py --bpm).
Outputs: music.wav, sfx.wav, mix_noVO.wav, mix_VO.wav (-16 LUFS masters), plan.json.
"""
import argparse, json, os, sys, tempfile
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.ndimage import uniform_filter1d
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from engine import dsp, theory as th
import score_v2 as V
from score_v2 import kick, hat, snare, bell, sub_note, pluck_note, put, sfx_sound, _push, st_loud, event_loud, \
    render_piano, master, duck_env, PENTA, SFX_REL
from score_v3 import supersaw_hit, swell, build_layers
import pads, scorecfg
SR = dsp.SR; BEAT, BAR = 0.5, 2.0
rng = np.random.default_rng(11)


def calls_from(loop, pickup, T):
    """chapter-head call per loop chord: (pickup = last 3 notes of the previous theme bar, phrase = theme bar)."""
    out = {}
    for i in range(0, 8, 2):
        pk = pickup if i == 0 else "r:1 " + " ".join(T[i - 1].split()[-3:])
        out.setdefault(loop[i], (pk, T[i]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stems", required=True, help="stems folder written by lib/post.py")
    ap.add_argument("--grid", required=True, help="grid json from grid_03a.py (same --bpm)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--music-config", help="per-episode JSON (scorecfg.py): key, bpm, progression, motif, pad, sections")
    ap.add_argument("--key"); ap.add_argument("--bpm", type=float); ap.add_argument("--pad"); ap.add_argument("--seed", type=int)
    a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    global BEAT, BAR, rng
    cfg = scorecfg.load(a.music_config, key=a.key, bpm=a.bpm, pad=a.pad, seed=a.seed)
    a.pad = cfg["pad"]
    BEAT = 60.0 / cfg["bpm"]; BAR = 4 * BEAT; q = BEAT / 0.5          # q scales the beat-relative offsets
    V.BPM, V.BEAT, V.BAR = cfg["bpm"], BEAT, BAR; V.KEY_SHIFT = cfg["shift"]
    rng = np.random.default_rng(cfg["seed"])
    TT = scorecfg.tonic_tones(cfg); V.PENTA = TT["penta"]
    PR, MO = cfg["progression"], cfg["motif"]
    LOOP, PICKUP, T = PR["loop"], MO["pickup"], MO["theme"]
    CR_MEL = T[0:4] + T[4:8] + T[0:3] + MO["coda"]
    CALL = calls_from(LOOP, PICKUP, T)
    tl = json.load(open(os.path.join(a.stems, "timeline.json")))
    act = json.load(open(os.path.join(a.stems, "vo_activity.json")))
    phi = json.load(open(a.grid))["fit_current"]["phase_offset_s"]
    total = tl["duration"]; n = int(round(total * SR)); tv = np.arange(n) / SR
    secs, thin, reveal = V.build_plan(tl, phi, cfg["sections"])
    S = {s["style"]: s for s in secs}
    T0 = phi - BAR
    bar_t = lambda k: T0 + k * BAR
    kof = lambda t: int(np.floor((t - T0 + 1e-6) / BAR))
    b, cl, rc, en = S["build"], S["climax"], S["recap"], S["end"]
    kcl, krc, ken = kof(cl["start"]), kof(rc["start"]), kof(en["start"])

    def chord(k):
        if k < 2: return PR["intro"]
        if k in (kcl - 2,): return PR["cadence"][0]
        if k in (kcl - 1, ken - 1): return PR["cadence"][1]
        if k >= ken: return PR["ending"]
        return LOOP[(k - 2) % 8]
    if chord(kcl) != LOOP[0]:   # the climax must land on the tonic (loop bar 1): nudge the loop phase if needed
        off = (kcl - 2) % 8
        _chord = chord
        def chord(k, _c=_chord, _o=off):
            return LOOP[(k - 2 - _o) % 8] if 2 <= k and k not in (kcl - 2, kcl - 1, ken - 1) and k < ken else _c(k)
    assert chord(kcl) == LOOP[0], "theme must start on the tonic"

    # ---- cue windows (layers per section; times from the timeline, snapped to bars)
    snap = lambda t: phi + np.floor((t - phi) / BAR) * BAR
    cap = {c.get("id"): c for c in tl["captions"]}
    err = [e["t"] for e in tl["sfx"] if e["name"] == "error"]
    ns_over = (snap(err[0]) - BAR, snap(err[0])) if err else (-1e9, -1e9)  # near-silence: the bar before the first error
    pauses = [(c["t"] - 0.3, c["end"] + 0.2) for c in tl["captions"] if c["en"].lower().startswith("pause and think")]
    try: o6 = snap(V.anchor_time(tl, cfg["pulse_groove_until"]))
    except (KeyError, ValueError): o6 = (S["pulse"]["start"] if "pulse" in S else 0.0) + 9 * BAR
    near = ([ns_over] if err else []) + pauses
    def layers(t):
        st = next((s for s in secs if s["start"] <= t < s["end"]), secs[-1]); sty = st["style"]
        if any(x <= t < y for x, y in near): return {}, sty, st
        if sty == "pulse":
            if t < o6: return dict(kick="1", sub="pulse", arp="8s", hat="off" if t >= st["start"] + 4 else ""), sty, st
            if t < ns_over[0]: return dict(arp="8s"), sty, st
            if t < st["end"] - BAR: return dict(sub="pulse"), sty, st
            return {}, sty, st
        if sty == "lift": return dict(hat="8", arp="8"), sty, st
        if sty == "code": return dict(kick="13", hat="off", arp="16", sub="pulse"), sty, st
        if sty == "code2": return dict(arp="8s"), sty, st
        if sty == "build": return build_layers(int((t - st["start"] + 1e-6) // BAR), st["bars"]), sty, st
        if sty == "climax": return dict(sub="8th", kick="4", hat="16", snare="24", arp="16"), sty, st
        return {}, sty, st
    CUT = dict(pulse=2300, lift=3000, code=2200, code2=2300, build=(2600, 4600), climax=5200)

    B = {k: np.zeros((n, 2), np.float32) for k in ("sub", "kick", "hat", "snare", "arp", "bell", "stab", "swell")}
    piano, kicks = [], []
    K = kof(total) + 2
    # ---- bed root (soft sustained) / sub pulse
    for k in range(0, K):
        t = bar_t(k)
        if t >= total: break
        _, pcs, bpc = th.chord(chord(k)); root = th.in_range(bpc, 33, 44)[0]
        L, sty, st = layers(t + 0.01); mode = L.get("sub", "")
        thin_now = any(x <= t + 0.1 < y for x, y in thin)
        if mode == "pulse" and not thin_now:
            put(B["sub"], sub_note(root, 0.9 * q), t, 1.0); put(B["sub"], sub_note(root, 0.7 * q), t + 0.75 * q, 0.7); put(B["sub"], sub_note(root, 0.4 * q), t + 1.5 * q, 0.6)
        elif mode == "8th" and not thin_now:
            for j in range(8): put(B["sub"], sub_note(root + (12 if j % 4 == 3 else 0), 0.22 * q), t + j * 0.25 * q, 0.9 if j % 2 == 0 else 0.65)
        else:
            put(B["sub"], sub_note(root, BAR), t, 0.45)
    # ---- the bed: pad X, continuous
    CH = [(chord(k), bar_t(k), bar_t(k) + BAR) for k in range(0, K)]
    raw = pads.BEDS[a.pad][1](CH, n, np.random.default_rng(99))
    bed_db = np.zeros(n); bed_lp = np.zeros(n)
    for x, y in near:
        m = (tv >= x) & (tv < y); bed_db[m] = -7; bed_lp[m] = 1
    bed_db = uniform_filter1d(bed_db, int(0.5 * SR)); bed_lp = uniform_filter1d(bed_lp, int(0.5 * SR))
    pad = raw * (1 - bed_lp[:, None]) + dsp.butter(raw, "lowpass", 500, 2) * bed_lp[:, None]
    pad = pad * dsp.db(bed_db)[:, None] * np.minimum(1, tv / 3.0)[:, None]

    # ---- drums + arps per beat
    pat, sparse = [0, 2, 1, 3, 2, 1, 3, 2], [1, 0, 1, 1, 0, 1, 0, 1]; pa = None
    for bi in range(int((total - T0) / BEAT)):
        t = T0 + bi * BEAT
        if t < 0 or t >= total - 1: continue
        L, sty, st = layers(t + 0.01); bib = bi % 4
        thin_now = any(x <= t < y for x, y in thin) and sty not in ("build",) and not (sty == "climax" and t < st["start"] + 0.01)
        x = (t - st["start"]) / max(1e-3, st["end"] - st["start"])
        kk = L.get("kick", "")
        if not thin_now and kk and (bib == 0 or (kk == "13" and bib == 2) or kk == "4"):
            put(B["kick"], kick(), t, 1.0 if bib == 0 else 0.82); kicks.append(t)
        h = L.get("hat", "")
        if not thin_now and h:
            put(B["hat"], hat(1.0, open_=(bib == 3 and h != "off")), t + 0.25 * q, 1.0, 0.3)
            if h in ("8", "16"): put(B["hat"], hat(), t, 0.5, -0.3)
            if h == "16": put(B["hat"], hat(), t + 0.125 * q, 0.35, 0.15); put(B["hat"], hat(), t + 0.375 * q, 0.35, -0.15)
        if not thin_now and L.get("snare") == "24" and bib in (1, 3): put(B["snare"], snare(), t, 1.0)
        am = L.get("arp", "")
        if am:
            _, pcs, _ = th.chord(chord(kof(t + 0.01)))
            v = sorted(th.voice(pcs, 62, 79, 4, pa, avoid_low_thirds=False)); pa = v
            c = CUT.get(sty, 2300); cut = c[0] + (c[1] - c[0]) * np.clip(x, 0, 1) if isinstance(c, tuple) else c
            I = 0.5 + 0.5 * (x if sty == "build" else (1.0 if sty == "climax" else 0.3))
            sub = 4 if am == "16" else 2
            for j in range(sub):
                tj = t + j * BEAT / sub; step = bi * sub + j
                if (any(p <= tj < q for p, q in thin) and sty != "build") or (am == "8s" and not sparse[step % 8]): continue
                m = v[pat[step % 8]] + (12 if am == "16" and (step // 8) % 2 else 0)
                g = (0.55 + 0.45 * I) * (1.0 if j == 0 else 0.8) * (0.7 if sty in ("code", "code2", "pulse") else 1.0)
                y = pluck_note(m, cut, g); pan = 0.35 * np.sin(step * 0.7)
                put(B["arp"], y, tj, 1.0, pan); put(B["arp"], y, tj + 0.375 * q, 0.28, -pan)
    # ---- snare roll over the last 2 bars, stopping at the dead stop (cut - 0.4 s)
    STOP = cl["start"] - 0.4
    t = cl["start"] - 2 * BAR; i = 0
    while t < STOP - 0.06:
        p = (t - (cl["start"] - 2 * BAR)) / (2 * BAR - 0.4)
        put(B["snare"], snare(0.25 + 0.75 * p ** 1.5), t, 1.0, 0.15 * np.sin(i))
        t += (0.25 if p < 0.25 else 0.125 if p < 0.6 else 0.0625) * q; i += 1
    put(B["swell"], swell(TT["swell"], BAR), STOP - BAR, 1.0)                   # reversed tonic swell -> dead stop
    for s in secs[1:]:
        if s["style"] in ("pulse", "lift", "code", "code2", "build", "recap"):
            put(B["swell"], swell(TT["swell"][:4], 1.4), s["cut"] - 1.4, 0.35)

    # ---- melody (v3 theme)
    def mel(bars, t0, vel=50, bell_amp=0.0, piano_on=True, oct_double=False):
        for i_, bar in enumerate(bars):
            for nm, b0, d in th.parse_bar(bar, 4):
                if nm == "r": continue
                p = th.note(nm); ts = t0 + i_ * BAR + b0 * BEAT; te = ts + d * BEAT
                if piano_on:
                    piano.append((p, ts + rng.normal(0, 0.005), te + 0.08, vel + rng.normal(0, 3)))
                    if oct_double: piano.append((p - 12, ts, te + 0.08, vel - 14))
                if bell_amp: put(B["bell"], bell(p + 12 if oct_double else p, 2.2, bell_amp), ts, 1.0, 0.2 * np.sin(p))
    mel([PICKUP] + T[0:3] + ["Bb4:4"], bar_t(1), 50, 0.2)                                   # title
    for s in secs[1:]:                                                                     # chapter-head call (+ response)
        if s["style"] not in ("pulse", "lift", "code", "code2"): continue
        k0 = kof(s["start"] + 0.01); pk, ph = CALL[chord(k0)]
        mel([pk, ph], s["start"] - BAR, 0, 0.75, piano_on=False)
        if s["style"] in ("pulse", "code"):
            r = CALL[chord(k0 + 2)][1]; mel([r], s["start"] + 2 * BAR, 46)
    Bb_ = b["bars"]
    for k in range(8, Bb_ - 8, 8):                                                         # build call / response
        mel([PICKUP, T[0]], b["start"] + (k - 1) * BAR, 0, 0.7, piano_on=False); mel([T[2]], b["start"] + (k + 2) * BAR, 52)
    tb = b["start"] + (Bb_ - 8) * BAR
    mel([PICKUP], tb - BAR, 60, 0.6)
    mel(T[:7] + ["E5:1 A4:1 D5:0.75 E5:0.45 r:0.8"], tb, 62, 0.6)                          # pickup ends before the dead stop
    mel(CR_MEL[:4], cl["start"], 92, 0.55, oct_double=True)
    mel(CR_MEL[4:13], rc["start"], 56, 0.18)
    mel(CR_MEL[13:], en["start"], 50, 0.25)
    for s in secs[1:]:
        _, pcs, bpc = th.chord(chord(kof(s["start"] + 0.01))); r = th.in_range(bpc, 38, 49)[0]
        piano += [(r, s["start"], s["start"] + 3.5, 50), (r + 7, s["start"] + 0.02, s["start"] + 3.5, 42)]
    for k in range(kof(rc["start"]), K):
        t = bar_t(k)
        if t >= total - 1: break
        _, pcs, bpc = th.chord(chord(k)); v = th.voice(pcs[:3], 50, 64, 3)
        piano += [(th.in_range(bpc, 38, 49)[0], t, t + BAR + 0.3, 44)] + [(p, t + BEAT * (i_ + 1), t + BAR + 0.3, 34) for i_, p in enumerate(v)]
    put(B["stab"], supersaw_hit(TT["hit"]), cl["start"], 1.0)
    piano += [(TT["low"][0], cl["start"], cl["start"] + 3, 96), (TT["low"][1], cl["start"], cl["start"] + 3, 90)]
    with tempfile.TemporaryDirectory() as tmp:
        P = render_piano(piano, n, tmp)

    # ---- mix (bus levels as in the approved PoC)
    duck = np.ones(n, np.float32); Ld = int(0.32 * SR); sh = 1 - 0.35 * np.exp(-np.arange(Ld) / (0.1 * SR))
    for t in kicks:
        i = int(t * SR); m = min(Ld, n - i)
        if m > 0: duck[i:i + m] = np.minimum(duck[i:i + m], sh[:m])
    g = lambda x, d: x * dsp.db(d - dsp.active_rms_db(x))
    pk = lambda x, d: x * dsp.db(d) / (np.abs(x).max() + 1e-9)
    mus = np.zeros((n, 2), np.float32); verb = np.zeros((n, 2), np.float32)
    def add(x, send, hp=None):
        nonlocal mus, verb
        if hp: x = dsp.butter(x, "highpass", hp, 2)
        mus += x; verb += x * send
    add(g(pad, -24) * duck[:, None], 0.35, 90)
    add(g(dsp.butter(B["sub"], "lowpass", 240, 2), -25) * duck[:, None], 0, 28)
    add(g(B["arp"], -31) * duck[:, None], 0.3, 200)
    add(g(B["bell"], -31), 0.5, 300)
    add(g(P, -22), 0.33, 45)
    add(pk(B["swell"], -14), 0.3); add(pk(B["stab"], -8), 0.45)
    add(pk(B["kick"], -9), 0.04); add(pk(B["hat"], -25), 0.12); add(pk(B["snare"], -17), 0.3)
    ir = dsp.make_ir(rt60=2.8, predelay=0.025, bright=0.35); ir = 0.55 * ir + 0.45 * ir.mean(1, keepdims=True)
    mus = mus + 0.5 * dsp.butter(dsp.butter(dsp.convolve(verb, ir), "highpass", 220, 2), "lowpass", 7000, 2)
    mus = dsp.eq(dsp.butter(mus, "highpass", 28, 2), "highshelf", 4500, 2.0)
    # macro: quiet title, build ramps in, climax on top, dropout dip
    gdb = np.zeros(n)
    gdb -= 3.0 * (tv < S["open"]["end"] - 0.5)
    m = (tv >= b["start"]) & (tv < cl["start"]); gdb[m] -= 2.0 * (1 - (tv[m] - b["start"]) / (cl["start"] - b["start"]))
    gdb -= 2.5 * ((tv > cl["start"] - BAR + 0.1) & (tv < cl["start"]))
    gdb += 3.0 * ((tv >= cl["start"]) & (tv < cl["end"] - 1.0))
    gdb = uniform_filter1d(gdb, int(0.25 * SR))
    gate = np.ones(n, np.float32)                                                          # 0.4 s dead stop
    i0, i1 = int(STOP * SR), int(cl["start"] * SR); r = int(0.01 * SR)
    gate[i0:i1] = 0.0; gate[i0 - r:i0] = np.linspace(1, 0, r); gate[i1 - r // 2:i1] = 0
    fo = int(3.0 * SR); fade = np.ones(n, np.float32); fade[-fo:] = np.linspace(1, 0, fo) ** 2
    mus = mus * (dsp.db(gdb) * gate * fade)[:, None]
    mus *= dsp.db(-17 - pyln.Meter(SR).integrated_loudness(mus))
    # ---- SFX (timeline cues; whooshes -6 dB; soft impacts at chapter cuts; big hit + 4-s riser + subdrop at the reveal)
    mloud = st_loud(mus); sfx = np.zeros((n, 2), np.float32); log = []
    ev = []; pi = qi = 0; last = None
    for e in tl["sfx"]:
        ch = max([c["num"] for c in tl["chapters"] if c["t"] <= e["t"] + 0.01] or [0])
        if ch != last: pi = qi = 0; last = ch
        nm = e["name"]; g0 = e.get("gain", 0) - (6 if nm == "whoosh" else 0)
        if STOP - 0.05 <= e["t"] < cl["start"] - 0.01: continue                            # nothing in the dead stop
        x = _push(PENTA[min(pi, len(PENTA) - 1)]) if nm == "push" else sfx_sound("pop", pop_i=qi) if nm == "pop" else sfx_sound(nm)
        pi += nm == "push"; qi += nm == "pop"
        ev.append((e["t"], nm, x, g0))
    for s in secs[1:]:
        if s["style"] == "end": continue
        ev.append((s["cut"], "impact", dsp.boom(int(3 * SR), 0, 1.0, rng), 3 if s["style"] == "climax" else -4))
    rl = 2 * BAR
    ev.append((STOP - rl, "riser", dsp.riser(int(rl * SR) + 10, 0, rl, 1.0, rng), 1))
    ev.append((cl["start"], "subdrop", sfx_sound("subdrop"), 0))
    for t, nm, x, g0 in ev:
        x = x if x.ndim == 2 else np.stack([x, x], 1)
        i0_ = int(max(0, t) * SR)
        ref = max(float(np.median(mloud[max(0, i0_ - int(1.5 * SR)):i0_ + int(1.5 * SR)])) if i0_ < n else -30, -30.0)
        put(sfx, x, t, dsp.db(ref + SFX_REL.get(nm, -10) + 0.5 * g0 - event_loud(x)))
        log.append(dict(t=round(t, 2), name=nm))
    sfx = sfx + 0.6 * dsp.butter(dsp.convolve(sfx * 0.25, ir), "highpass", 250, 2)
    sfx[i0:i1] *= 0.0                                                                       # the dead stop is silent
    # ---- outputs
    vo, _ = sf.read(os.path.join(a.stems, "vo.wav"), dtype="float32", always_2d=True)
    vo = np.pad(vo, ((0, max(0, n - len(vo))), (0, 0)))[:n]
    sf.write(os.path.join(a.outdir, "music.wav"), master(mus.copy()), SR, subtype="PCM_24")
    sf.write(os.path.join(a.outdir, "sfx.wav"), sfx, SR, subtype="FLOAT")
    sf.write(os.path.join(a.outdir, "mix_noVO.wav"), master(mus + sfx), SR, subtype="PCM_24")
    d = duck_env(n, act, -10.0); ds = duck_env(n, act, -3.0)
    sf.write(os.path.join(a.outdir, "mix_VO.wav"), master(vo + mus * dsp.db(-2) * d[:, None] + sfx * ds[:, None]), SR, subtype="PCM_24")
    plan = dict(version="v4", music_config={k: v for k, v in cfg.items()}, pad=a.pad, phase=phi, dead_stop=[STOP, cl["start"]], near_silences=near, o6=o6,
                sections=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()} for s in secs],
                chords=[(round(bar_t(k), 2), chord(k)) for k in range(K)], sfx=log, kicks=len(kicks))
    json.dump(plan, open(os.path.join(a.outdir, "plan.json"), "w"), indent=1, default=float)
    print("done", a.outdir, "dead stop", round(STOP, 2), "->", round(cl["start"], 2), "near", [(round(x, 2), round(y, 2)) for x, y in near])


if __name__ == "__main__":
    main()
