#!/usr/bin/env python3
"""Technical QA for a rendered bed: loudness / true peak (ffmpeg ebur128), spectral balance,
clipping, silence gaps, key check from the note JSON, spectrogram PNG."""
import json, os, re, subprocess, sys
import numpy as np, soundfile as sf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.theory import pc_of, nname


def main(wav):
    base = os.path.splitext(wav)[0]
    x, sr = sf.read(wav, dtype="float32", always_2d=True)
    r = subprocess.run(["ffmpeg", "-nostats", "-i", wav, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    summ = r[r.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
    LRA = float(re.search(r"LRA:\s+(-?[\d.]+) LU", summ).group(1))
    TP = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ).group(1))
    mono = x.mean(1)
    clip = int(np.sum(np.abs(x) >= 0.999))
    # silence gaps (exclude first 0.5 s and final 3 s tail)
    w = int(0.25 * sr)
    k = len(mono) // w
    rms = 20 * np.log10(np.sqrt((mono[: k * w].reshape(k, w) ** 2).mean(1)) + 1e-12)
    inner = rms[2: k - 12]
    gaps = int(np.sum(inner < -50))
    # spectrum balance (Welch, share of energy per band)
    f, P = signal.welch(mono, sr, nperseg=8192)
    bands = [(20, 60, "sub"), (60, 250, "low"), (250, 2000, "mid"), (2000, 6000, "hi-mid"), (6000, 20000, "air")]
    tot = P[(f >= 20) & (f < 20000)].sum()
    share = {n: 10 * np.log10(P[(f >= a) & (f < b)].sum() / tot) for a, b, n in bands}
    # spectral slope per octave 100 Hz - 8 kHz (pink ~ -3 dB/oct in band-energy-per-Hz terms)
    sel = (f > 100) & (f < 8000)
    slope = np.polyfit(np.log2(f[sel]), 10 * np.log10(P[sel] + 1e-20), 1)[0]
    rep = dict(file=wav, dur=round(len(x) / sr, 2), lufs_I=I, LRA=LRA, true_peak_dBTP=TP, clipped_samples=clip,
               silent_250ms_windows=gaps, band_share_dB={k_: round(v, 1) for k_, v in share.items()},
               psd_slope_dB_per_oct=round(slope, 2))
    js = base + ".json"
    if os.path.exists(js):
        d = json.load(open(js))
        allowed = {pc_of(n) for n in d["allowed"].split()}
        bad = []
        for tr, lst in d["notes"].items():
            for p, t0, t1, v in lst:
                if p % 12 not in allowed:
                    bad.append((tr, nname(p), round(t0, 2)))
        rep["notes_total"] = sum(len(v) for v in d["notes"].values())
        rep["out_of_key_notes"] = bad[:10]
        rep["out_of_key_count"] = len(bad)
        rep["pitch_range"] = [nname(min(p for l in d["notes"].values() for p, *_ in l)),
                              nname(max(p for l in d["notes"].values() for p, *_ in l))]
    # spectrogram
    fig, ax = plt.subplots(2, 1, figsize=(14, 7), gridspec_kw=dict(height_ratios=[3, 1]))
    ff, tt, S = signal.spectrogram(mono, sr, nperseg=4096, noverlap=3072)
    ax[0].pcolormesh(tt, ff, 10 * np.log10(S + 1e-14), vmin=-130, vmax=-40, shading="auto", cmap="magma")
    ax[0].set_yscale("symlog", linthresh=200); ax[0].set_ylim(30, 20000); ax[0].set_ylabel("Hz")
    ax[0].set_title(os.path.basename(wav) + f"  I={I} LUFS  TP={TP} dBTP")
    ax[1].plot(np.arange(k) * 0.25, rms); ax[1].set_ylabel("RMS dB"); ax[1].set_xlabel("s"); ax[1].set_ylim(-70, 0)
    plt.tight_layout(); plt.savefig(base + "_spectrogram.png", dpi=80)
    print(json.dumps(rep, indent=1, default=float))
    return rep


if __name__ == "__main__":
    for w in sys.argv[1:]:
        main(w)
