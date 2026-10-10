#!/usr/bin/env python3
"""Short music bed / audition: the chosen pad over the episode progression + the motif on Salamander piano.
Uses the same music config as score_v4.py (scorecfg.py), so it is a quick way to audition key / tempo / motif / pad
before scoring a whole episode, and it is what install.sh's smoke test renders (5 s).

  python bed.py --seconds 5 --out bed.wav [--music-config music.json] [--key "E minor"] [--bpm 100] [--pad X2] [--no-piano]
"""
import argparse, os, sys, tempfile
import numpy as np, soundfile as sf, pyloudnorm as pyln
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from engine import dsp, theory as th
import score_v2 as V
import pads, scorecfg

ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=16.0); ap.add_argument("--out", required=True)
ap.add_argument("--music-config"); ap.add_argument("--key"); ap.add_argument("--bpm", type=float)
ap.add_argument("--pad"); ap.add_argument("--seed", type=int); ap.add_argument("--no-piano", action="store_true")
ap.add_argument("--lufs", type=float, default=-16.0)
a = ap.parse_args()
cfg = scorecfg.load(a.music_config, key=a.key, bpm=a.bpm, pad=a.pad, seed=a.seed)
SR = dsp.SR; BEAT = 60.0 / cfg["bpm"]; BAR = 4 * BEAT; V.BPM = cfg["bpm"]
n = int(round(a.seconds * SR)); K = int(np.ceil(a.seconds / BAR)) + 1
loop = cfg["progression"]["loop"]
CH = [(cfg["progression"]["intro"] if k == 0 else loop[(k - 1) % 8], k * BAR, (k + 1) * BAR) for k in range(K)]
bed = pads.BEDS[cfg["pad"]][1](CH, n, np.random.default_rng(cfg["seed"]))
mix = bed * dsp.db(-24 - dsp.active_rms_db(bed))
if not a.no_piano:
    notes, bars = [], [cfg["motif"]["pickup"]] + cfg["motif"]["theme"]
    for i, bar in enumerate(bars):
        for nm, b0, d in th.parse_bar(bar, 4):
            if nm == "r": continue
            ts = i * BAR + b0 * BEAT
            if ts < a.seconds - 0.3: notes.append((th.note(nm), ts, min(ts + d * BEAT + 0.08, a.seconds), 54))
    with tempfile.TemporaryDirectory() as tmp:
        if not os.path.exists(V.SAL): raise SystemExit(f"Salamander SF2 missing: {V.SAL} (run install.sh or set CVS_SF2)")
        P = V.render_piano(notes, n, tmp)
    mix = mix + P * dsp.db(-22 - dsp.active_rms_db(P))
ir = dsp.make_ir(rt60=2.4, predelay=0.02, bright=0.35)
mix = mix + 0.35 * dsp.butter(dsp.convolve(mix * 0.3, ir), "highpass", 220, 2)[:n]
fo = min(n // 3, int(1.5 * SR)); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
fi = int(0.3 * SR); mix[:fi] *= np.linspace(0, 1, fi)[:, None]
mix *= dsp.db(a.lufs - pyln.Meter(SR).integrated_loudness(mix))
pk = np.abs(mix).max(); mix = mix * min(1.0, dsp.db(-1.5) / max(pk, 1e-9))
sf.write(a.out, mix.astype(np.float32), SR, subtype="PCM_24")
print(f"wrote {a.out} {a.seconds:.1f}s  key-shift {cfg['shift']:+d}  {cfg['bpm']} BPM  pad {cfg['pad']}  peak {20*np.log10(np.abs(mix).max()):.1f} dBFS")
