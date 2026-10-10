"""Audio stems + mixing for DSA episodes (used by post.py; also a standalone CLI to drop in music later).

Stem layout (written by post.py into out/<ep>_stems/):
  picture.mp4          finished picture, no audio (captions burned)
  vo.wav               English VO placed on the timeline, 48 kHz stereo, normalised to -16 LUFS
  sfx.wav              sound design, 48 kHz stereo, absolute level (about -32 LUFS integrated)
  vo_activity.json     VO intervals (gaps < 1.5 s merged) - drives music ducking
  music_placeholder.wav  synthesised neutral pad (for testing the slot; not in the deliverables)
  timeline.json, captions.srt

Mix rules: music normalised to -16 LUFS integrated, fades in/out; in the VO variant it is ducked -10 dB
under VO (80 ms attack / 400 ms release). The final mix is 2-pass loudnorm'd to -16 LUFS / -1.5 dBTP.

CLI (re-mix with a composed score, no re-render):
  python lib/mix.py out/03a_stems --music path/to/score.wav --out out/03a_stacks_v2 [--music-start 0] [--music-db 0] [--duck-db -10]
  -> out/03a_stacks_v2_noVO.mp4 and out/03a_stacks_v2_VO.mp4
"""
import argparse, json, os, subprocess, re
import numpy as np, soundfile as sf

SR = 48000

def sh(cmd):
    print("+", " ".join(cmd)[:300], flush=True)
    subprocess.run(cmd, check=True)

def load_audio(path, start=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", path]
    if dur: cmd += ["-t", f"{dur:.3f}"]
    raw = subprocess.check_output(cmd + ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"])
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

def lufs(x):
    """Integrated loudness (EBU R128) of a float stereo array, via ffmpeg ebur128."""
    tmp = "/tmp/_lufs.wav"; sf.write(tmp, x, SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", r.stderr)
    return float(m[-1]) if m and m[-1] != "-inf" else -70.0

def norm_to(x, target):
    l = lufs(x)
    return x * 10 ** ((target - l) / 20) if l > -69 else x

def activity(vo_events, gap=1.5, pre=0.1, post=0.15):
    iv = sorted([(e["t"] - pre, e["t"] + e["dur"] + post) for e in vo_events])
    out = []
    for a, b in iv:
        if out and a - out[-1][1] < gap: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out

def duck_env(n, intervals, depth_db=-10.0, attack=0.08, release=0.4):
    g = np.zeros(n, np.float32)
    for a, b in intervals:
        g[max(0, int(a * SR)):min(n, int(b * SR))] = 1.0
    # asymmetric one-pole smoothing (attack when rising, release when falling), run on a 1 kHz grid
    step = SR // 1000
    gs = g[::step].copy(); out = np.zeros_like(gs); v = 0.0
    ka, kr = 1 - np.exp(-1 / (attack * 1000)), 1 - np.exp(-1 / (release * 1000))
    for i, t in enumerate(gs):
        v += (t - v) * (ka if t > v else kr); out[i] = v
    env = np.repeat(out, step)[:n]
    if len(env) < n: env = np.pad(env, (0, n - len(env)), mode="edge")
    return 10 ** (depth_db * env / 20)

def prep_music(path, n, start=0.0, db=0.0, fade_in=0.5, fade_out=3.0):
    dur = n / SR
    m = load_audio(path, start, dur)
    if len(m) < n: m = np.pad(m, ((0, n - len(m)), (0, 0)))
    m = m[:n]
    m = norm_to(m, -16.0) * 10 ** (db / 20)
    fi, fo = min(int(fade_in * SR), n // 4), min(int(fade_out * SR), n // 3)   # clamp for very short clips
    m[:fi] *= np.linspace(0, 1, fi)[:, None]
    m[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return m

def placeholder_pad(n, seed=0):
    """Neutral, unobtrusive placeholder pad (Am-F-C-G, slow swells, low-passed). Not for release."""
    t = np.arange(n) / SR
    roots = [220.0, 174.61, 130.81, 196.0]          # A3 F3 C3 G3
    quals = [(0, 3, 7), (0, 4, 7), (0, 4, 7), (0, 4, 7)]
    seg = 8.0
    y = np.zeros(n)
    for k in range(int(np.ceil(n / SR / seg)) + 1):
        a, b = int(k * seg * SR), min(n, int((k + 1) * seg * SR + 2 * SR))
        if a >= n: break
        tt = t[a:b] - k * seg
        env = np.minimum(1, tt / 2.5) * np.clip((seg + 2 - tt) / 2.5, 0, 1)
        r = roots[k % 4]
        for semi in quals[k % 4]:
            f = r * 2 ** (semi / 12)
            for det in (-0.6, 0.6):
                y[a:b] += env * np.sin(2 * np.pi * (f + det) * tt) * 0.08
        y[a:b] += env * np.sin(2 * np.pi * r / 2 * tt) * 0.06
    from scipy.signal import butter, lfilter
    bb, aa = butter(2, 1200 / (SR / 2)); y = lfilter(bb, aa, y)
    st = np.stack([y, np.roll(y, 480)], 1).astype(np.float32)
    return norm_to(st, -16.0)

def final(x, out_m4a, normalise=True, target=-16.0, tp=-1.5):
    tmp = out_m4a + ".wav"; sf.write(tmp, x, SR, subtype="FLOAT")
    if normalise:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af",
                            f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
        js = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
        af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
              f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true,")
    else:
        af = ""
    af += f"alimiter=limit={10 ** ((tp - 0.3) / 20):.4f}:attack=3:release=50:level=false"
    sh(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", out_m4a])
    os.remove(tmp)

def mux(picture, m4a, out, title="Stacks"):
    sh(["ffmpeg", "-y", "-v", "error", "-i", picture, "-i", m4a, "-map", "0:v", "-map", "1:a", "-c", "copy",
        "-map_metadata", "-1", "-map_chapters", "-1", "-metadata", f"title={title}", "-metadata:s:a:0", "language=eng",
        "-shortest", "-movflags", "+faststart", out])

def render_variants(stems, out_prefix, music=None, music_start=0.0, music_db=0.0, duck_db=-10.0, variants=("noVO", "VO"), title=None):
    vo = sf.read(os.path.join(stems, "vo.wav"), dtype="float32")[0]
    sfx = sf.read(os.path.join(stems, "sfx.wav"), dtype="float32")[0]
    n = len(sfx)
    act = json.load(open(os.path.join(stems, "vo_activity.json")))
    m = prep_music(music, n, music_start, music_db) if music else None
    outs = []
    for v in variants:
        mix = sfx.copy()
        if v == "VO":
            mix += vo[:n]
            if m is not None: mix += m * duck_env(n, act, duck_db)[:, None]
        elif m is not None:
            mix += m
        # SFX-only (no VO, no music) is left at its designed absolute level instead of being pushed up to -16
        a = os.path.join(stems, f"mix_{v}.m4a")
        final(mix, a, normalise=(v == "VO" or m is not None))
        o = f"{out_prefix}_{v}.mp4"; mux(os.path.join(stems, "picture.mp4"), a, o, title or os.path.basename(out_prefix)); outs.append(o)
    return outs

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stems"); ap.add_argument("--out", required=True, help="output prefix, e.g. out/03a_stacks_v2")
    ap.add_argument("--music"); ap.add_argument("--music-start", type=float, default=0.0)
    ap.add_argument("--music-db", type=float, default=0.0, help="trim relative to -16 LUFS")
    ap.add_argument("--duck-db", type=float, default=-10.0)
    ap.add_argument("--variants", nargs="+", default=["noVO", "VO"])
    ap.add_argument("--title", help="MP4 title metadata (default: output name)")
    a = ap.parse_args()
    for o in render_variants(a.stems, a.out, a.music, a.music_start, a.music_db, a.duck_db, a.variants, a.title): print("DONE", o)
