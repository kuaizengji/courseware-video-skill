"""Safe-margin QA: flag times where content pixels fall inside the outer margin.

Usage: python lib/edgescan.py <video> [--fps 4] [--margin 80]
Works at 1/4 scale (480x270). Content = dark (lum<170) or saturated (max-min>50) pixels.
Exclusions: the chapter-label HUD (top-left, 1000x120 px @1080p) and the caption band (y>820).
"""
import subprocess, sys, numpy as np, argparse
ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--fps", type=float, default=4)
ap.add_argument("--margin", type=int, default=80); ap.add_argument("--min", type=int, default=12)
a = ap.parse_args()
W, H, S = 480, 270, 4
m = a.margin // S
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"fps={a.fps},scale={W}:{H}:flags=area",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
i = 0; hits = []
while True:
    buf = p.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(int)
    lum = f @ np.array([0.299, 0.587, 0.114]); sat = f.max(2) - f.min(2)
    c = (lum < 170) | (sat > 50)
    c[205:, :] = False                       # caption band
    c[:30, :250] = False                     # chapter HUD
    reg = {"L": c[:, :m], "R": c[:, W - m:], "T": c[:m, :], "B": c[H - m:205, :] if H - m < 205 else c[:0]}
    bad = {k: int(v.sum()) for k, v in reg.items() if v.sum() >= a.min}
    if bad: hits.append((i / a.fps, bad))
    i += 1
# merge into ranges
rng = []
for t, b in hits:
    if rng and t - rng[-1][1] <= 1.0 / a.fps + 1e-6:
        rng[-1][1] = t; rng[-1][2] |= set(b)
    else: rng.append([t, t, set(b)])
for s, e, k in rng: print(f"{s:7.2f}-{e:7.2f}  {''.join(sorted(k))}")
print(f"{len(rng)} ranges, {len(hits)} frames flagged of {i}")
