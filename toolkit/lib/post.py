"""
Episode finishing pipeline v2 (reusable for every DSA episode).

  python $CVS_HOME/toolkit/lib/post.py <episode_dir> --name 03a_stacks --stems out/03a_stems --scenes S00 S01 ...
                     [--music path.wav] [--music-start 0] [--music-db 0] [--en-subs] [--skip-video]

 1. concat rendered Manim scenes (<ep>/media/videos/scenes/1080p30/<Scene>.mp4)
 2. merge per-scene timelines (<ep>/build/timeline/<Scene>.json): captions, chapter labels, VO + SFX cues
 3. captions.ass: bilingual captions - Chinese explanation line + English line beneath (= the VO text) - and the
    chapter label overlay (top-left, English first), styled per theme
 4. picture finishing per theme
      light: background gradient + faint drifting dot grid + soft vignette (multiply plate),
             soft bottom band behind captions, very fine grain, captions, fades from the bg colour
      dark : bloom + star plate keyed into the flat background (v1 look)
 5. stems (vo.wav, sfx.wav, vo_activity.json, music_placeholder.wav, picture.mp4) -> <stems>
 6. variants via lib/mix.py: out/<name>_noVO.mp4 and out/<name>_VO.mp4 (with --music: score mixed in,
    -16 LUFS, ducked -10 dB under VO)
"""
import argparse, json, os, subprocess, shutil
import numpy as np, soundfile as sf
sys_path = os.path.dirname(os.path.abspath(__file__))
import sys; sys.path.insert(0, sys_path)
import mix
import cvs_config as C

LIB = sys_path
ROOT = C.TOOLKIT          # toolkit root: assets/ live in toolkit/assets
SR = mix.SR
SFX_BASE_DB = dict(whoosh=-19, click=-25, push=-21, pop=-21, chime=-23, chime_hi=-25, chime_lo=-22,
                   error=-19, tick=-27, type=-29, swell=-20, boom=-18)
SFX_TARGET_LUFS = -32.0

def sh(cmd, **kw):
    print("+", cmd if isinstance(cmd, str) else " ".join(cmd)[:300], flush=True)
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, **kw)

def probe_dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", p]).decode().strip())

def hex2rgb(h): h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
def ass_col(h, a=0):
    r, g, b = hex2rgb(h).astype(int); return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"

# ---------------- plates ----------------
def make_plate_dark(path, W=2112, H=1188, seed=3):
    from PIL import Image, ImageFilter
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    for cx, cy, r, col in ((0.42, 0.38, 0.55, (3, 7, 16)), (0.75, 0.7, 0.4, (2, 8, 12)), (0.2, 0.8, 0.35, (5, 5, 12))):
        d = ((xx - cx * W) ** 2 + (yy - cy * H) ** 2) / (r * W) ** 2
        img += np.exp(-d * 2.2)[..., None] * np.array(col, np.float32)
    star = np.zeros((H, W), np.float32); n = 1400
    star[rng.integers(0, H, n), rng.integers(0, W, n)] = rng.uniform(0.15, 1, n) ** 3 * 255
    s1 = np.array(Image.fromarray(star.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) * 2.2
    big = np.zeros((H, W), np.float32); big[rng.integers(0, H, 40), rng.integers(0, W, 40)] = 255
    s2 = np.array(Image.fromarray(big.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2)), np.float32) * 6
    img += (s1 * 0.55 + s2 * 0.5)[..., None] * np.array([0.75, 0.85, 1.0], np.float32)
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(path)

def make_plate_light(path, bg_top, bg_bot, W=2112, H=1188, seed=5, grid=30):
    """Multiply plate: vertical gradient (relative to the flat Manim bg = bg_top), faint dot grid,
    sparse fine specks, soft vignette. White = no change."""
    from PIL import Image, ImageFilter
    rng = np.random.default_rng(seed)
    top, bot = hex2rgb(bg_top), hex2rgb(bg_bot)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = (yy / (H - 1))[..., None]
    grad = (1 - v) * 1.0 + v * (bot / top)                      # factor per channel
    # dot grid
    dots = np.zeros((H, W), np.float32)
    dots[(grid // 2)::grid, (grid // 2)::grid] = 1.0
    specks = np.zeros((H, W), np.float32); n = 900
    specks[rng.integers(0, H, n), rng.integers(0, W, n)] = rng.uniform(0.3, 1.0, n)
    dimg = Image.fromarray((dots * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    simg = Image.fromarray((specks * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    d = np.array(dimg, np.float32) / 255 * 2.6
    s = np.array(simg, np.float32) / 255 * 2.0
    tint = np.array([0.80, 0.84, 0.95], np.float32)          # cool blue-gray marks
    mark = 1 - (np.clip(d, 0, 1) * 0.13 + np.clip(s, 0, 1) * 0.10)[..., None] * (1 - tint * 0.6)
    # vignette (soft, cool)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = 1 - 0.075 * np.clip((r - 0.55) / 0.85, 0, 1) ** 1.6
    vig = vig[..., None] * np.array([0.992, 0.995, 1.0], np.float32) ** np.clip(r - 0.5, 0, 1)[..., None]
    out = grad * mark * vig
    out = out * 255 + rng.uniform(-0.5, 0.5, out.shape)          # dither: no banding
    Image.fromarray(np.round(out).clip(0, 255).astype(np.uint8)).save(path)

def make_caption_band(path, W=1920, H=1080, y0=830, alpha=0.78, color="#FFFFFF"):
    from PIL import Image
    a = np.zeros((H, W), np.float32)
    yy = np.arange(H, dtype=np.float32)
    ramp = np.clip((yy - y0) / (H - y0), 0, 1) ** 1.3 * alpha
    a[:] = ramp[:, None]
    rgb = np.broadcast_to(hex2rgb(color), (H, W, 3))
    a = a * 255 + np.random.default_rng(1).uniform(-0.5, 0.5, a.shape)
    img = np.concatenate([rgb, np.round(a).clip(0, 255)[..., None]], 2).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(path)

# ---------------- captions + chapter labels ----------------
def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def _vw(t): return sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in t)

def split_zh(t, maxw=36):
    if _vw(t) <= maxw: return t
    mid = _vw(t) / 2; best, bd = None, 1e9; acc = 0
    for i, ch in enumerate(t):
        acc += _vw(ch)
        if ch in "，；：、" and abs(acc - mid) < bd: best, bd = i, abs(acc - mid)
    return t if best is None else t[:best + 1] + "\\N" + t[best + 1:]

def split_en(t, maxc=100):
    if len(t) <= maxc: return t
    mid = len(t) / 2
    cands = [m for m in range(len(t)) if t[m] == " " and t[m - 1] in ",;:—-."] or [m for m in range(len(t)) if t[m] == " "]
    k = min(cands, key=lambda m: abs(m - mid))
    return t[:k] + "\\N" + t[k + 1:]

STYLE = {
    "light": dict(zh_c="#141C36", zh_o="#FFFFFF", en_c="#26324F", num="#A86A00", ttl="#141C36", sub="#46536F",
                  rule="#2F55D4", outline=3.0, blur=1.6, shadow=0),
    "dark": dict(zh_c="#ECF0F4", zh_o="#050810", en_c="#B4C2D2", num="#F3C46A", ttl="#E9EDF5", sub="#7C88A3",
                 rule="#63D2FF", outline=0, blur=0.6, shadow=1.2),
}

def write_ass(caps, chapters, path, theme="light", en_subs=True):
    S = STYLE[theme]
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ZH,Noto Serif CJK SC,46,{ass_col(S['zh_c'])},&H000000FF,{ass_col(S['zh_o'], 0x30)},&H96000000,-1,0,0,0,100,100,2,0,1,{S['outline']},{S['shadow']},2,80,80,92,1
Style: EN,Inter Medium,28,{ass_col(S['en_c'])},&H000000FF,{ass_col(S['zh_o'], 0x30)},&H96000000,0,0,0,0,100,100,0.3,0,1,{S['outline'] * 0.8},{S['shadow']},2,80,80,46,1
Style: CH,Inter SemiBold,32,{ass_col(S['ttl'])},&H000000FF,{ass_col(S['zh_o'], 0x40)},&H00000000,0,0,0,0,100,100,5,0,1,{S['outline'] * 0.6},0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    L = []
    for c in caps:
        a, b = ass_time(c["t"] + 0.05), ass_time(c["end"] - 0.02)
        e = split_en(c.get("en", "")) if en_subs else ""
        zmv = (92 + (34 if "\\N" in e else 0)) if e else 62
        L.append(f"Dialogue: 1,{a},{b},ZH,,0,0,{zmv},,{{\\fad(120,100)\\blur{S['blur']}}}{split_zh(c['zh'])}")
        if e:
            L.append(f"Dialogue: 1,{a},{b},EN,,0,0,0,,{{\\fad(120,100)\\blur{S['blur'] * 0.7}}}{e}")
    for ch in chapters:
        a, b = ass_time(ch["t"] + 0.1), ass_time(ch["end"])
        en_t = ch["en"].upper()
        txt = (f"{{\\fnJetBrains Mono\\b1\\fs32\\fsp1\\c{ass_col(S['num'])}}}{ch['num']:02d}{{\\r}}   "
               f"{en_t}   {{\\fnNoto Serif CJK SC\\b1\\fs30\\fsp2\\c{ass_col(S['ttl'])}}}{ch['zh']}")
        w = int(32 * 2 * 0.62 + 50 + len(en_t) * 27 + 40 + len(ch["zh"]) * 32 + 20)
        # soft white backing plate (contrast on the light background), then text, then the accent rule
        L.append(f"Dialogue: 1,{a},{b},CH,,0,0,0,,{{\\pos(66,38)\\fad(250,250)\\c&HFFFFFF&\\alpha&H48&\\bord0\\shad0\\blur6\\p1}}"
                 f"m 0 0 l {w + 44} 0 l {w + 44} 76 l 0 76{{\\p0}}")
        L.append(f"Dialogue: 2,{a},{b},CH,,0,0,0,,{{\\move(76,52,88,52,0,450)\\fad(250,250)\\blur{S['blur'] * 0.4}}}{txt}")
        L.append(f"Dialogue: 2,{a},{b},CH,,0,0,0,,{{\\pos(88,104)\\fad(250,250)\\c{ass_col(S['rule'])}\\alpha&H00&\\bord0\\shad0"
                 f"\\clip(0,0,88,1080)\\t(120,800,\\clip(0,0,{88 + w},1080))\\p1}}m 0 0 l {w} 0 l {w} 4 l 0 4{{\\p0}}")
    open(path, "w").write(hdr + "\n".join(L) + "\n")

def write_srt(caps, path):
    def ts(t):
        ms = int(round(t * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
    out = [f"{i}\n{ts(c['t'])} --> {ts(c['end'])}\n{c['zh']}\n{c.get('en','')}\n" for i, c in enumerate(caps, 1)]
    open(path, "w").write("\n".join(out))

# ---------------- picture ----------------
def finish_light(raw, plate, band, ass, out, dur, bg="#F4F6FA"):
    fc = (
        "[1:v]format=gbrp,crop=1920:1080:x='96+80*sin(t/41)':y='54+40*sin(t/53+1)',format=gbrp[pl];"
        "[0:v]format=gbrp[v0];"
        "[v0][pl]blend=all_mode=multiply[m];"
        "[m]format=rgba[mr];[mr][2:v]overlay=format=auto[b];"
        f"[b]format=yuv420p,noise=c0s=1:c0f=t,ass='{ass}',"
        f"fade=t=in:d=0.6:color=0x{bg.lstrip('#')},fade=t=out:st={dur - 0.8:.3f}:d=0.8:color=0x{bg.lstrip('#')}[v]"
    )
    sh(["ffmpeg", "-y", "-v", "error", "-i", raw, "-loop", "1", "-framerate", "30", "-i", plate,
        "-loop", "1", "-framerate", "30", "-i", band,
        "-filter_complex", fc, "-map", "[v]", "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-tune", "film", "-maxrate", "14M", "-bufsize", "28M",
        "-pix_fmt", "yuv420p", "-an", out])

def finish_dark(raw, plate, ass, out, dur):
    fc = (
        "[0:v]format=gbrp,split=4[base][g1][g2][mk];"
        "[g1]lutrgb=r='max(val-34\\,0)*1.5':g='max(val-34\\,0)*1.5':b='max(val-34\\,0)*1.5',gblur=sigma=7[gl1];"
        "[g2]scale=480:270,lutrgb=r='max(val-30\\,0)*1.6':g='max(val-30\\,0)*1.6':b='max(val-30\\,0)*1.6',"
        "gblur=sigma=9,scale=1920:1080,format=gbrp[gl2];"
        "[base][gl1]blend=all_mode=screen:all_opacity=0.55[b1];[b1][gl2]blend=all_mode=screen:all_opacity=0.55[bl];"
        "[1:v]format=gbrp,crop=1920:1080:x='96+90*sin(t/47)':y='54+44*sin(t/61+1)'[pl];"
        "[bl]split[bl1][bl2];[bl1][pl]blend=all_mode=addition[st];"
        "[mk]format=gray,lut=y='clip((44-val)*255/26\\,0\\,255)',gblur=sigma=3,format=gbrp[m];"
        "[bl2][st][m]maskedmerge[cmp];"
        "[cmp]format=yuv420p,vignette=angle=PI/4.6:mode=forward,noise=c0s=2:c0f=t,"
        f"ass='{ass}',fade=t=in:d=0.6,fade=t=out:st={dur - 0.8:.3f}:d=0.8[v]")
    sh(["ffmpeg", "-y", "-v", "error", "-i", raw, "-loop", "1", "-framerate", "30", "-i", plate,
        "-filter_complex", fc, "-map", "[v]", "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-tune", "film", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-an", out])

# ---------------- audio stems ----------------
def build_sfx(events, n, sfx_dir):
    out = np.zeros((n, 2), np.float32); cache = {}
    for e in events:
        nm = e["name"]
        if nm not in cache: cache[nm] = sf.read(os.path.join(sfx_dir, nm + ".wav"), dtype="float32")[0]
        s = cache[nm]
        if s.ndim == 1: s = np.stack([s, s], 1)
        g = 10 ** ((SFX_BASE_DB.get(nm, -24) + e.get("gain", 0) + 6) / 20)
        i = int(e["t"] * SR)
        if i >= n: continue
        j = min(n, i + len(s)); out[i:j] += s[:j - i] * g
    return mix.norm_to(out, SFX_TARGET_LUFS)

def build_vo(events, n, vo_dir):
    from scipy.signal import resample_poly
    out = np.zeros((n, 2), np.float32)
    for e in events:
        x, sr = sf.read(os.path.join(vo_dir, e["id"] + ".wav"), dtype="float32")
        if sr != SR: x = resample_poly(x, SR // 8000, sr // 8000).astype(np.float32)
        i = int(e["t"] * SR); j = min(n, i + len(x))
        out[i:j, 0] += x[:j - i]; out[i:j, 1] += x[:j - i]
    return mix.norm_to(out, -16.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep"); ap.add_argument("--name", required=True); ap.add_argument("--stems", required=True)
    ap.add_argument("--out-dir", default=os.path.join(C.PROJECT, "out"), help="default: $CVS_PROJECT/out or ./out")
    ap.add_argument("--scenes", nargs="+", required=True)
    ap.add_argument("--video-dir", default="media/videos/scenes/1080p30")
    ap.add_argument("--music"); ap.add_argument("--music-start", type=float, default=0); ap.add_argument("--music-db", type=float, default=0)
    ap.add_argument("--no-en-subs", dest="en_subs", action="store_false",
                    help="drop the English caption line (default: bilingual - Chinese line + English line = the VO text)")
    ap.add_argument("--skip-video", action="store_true")
    a = ap.parse_args()
    ep = os.path.abspath(a.ep); b = os.path.join(ep, "build"); os.makedirs(b, exist_ok=True)
    stems = os.path.abspath(a.stems); os.makedirs(stems, exist_ok=True)
    lst, caps, sfx, vo, chaps, off, theme = [], [], [], [], [], 0.0, "light"
    markers = {"starts": {}, "caps": {}, "ev": []}
    for s in a.scenes:
        mp4 = os.path.join(ep, a.video_dir, s + ".mp4")
        tl = json.load(open(os.path.join(b, "timeline", s + ".json")))
        theme = tl.get("theme", theme)
        d = probe_dur(mp4)
        markers["starts"][s] = off
        for e in tl["events"]:
            e = dict(e); e["t"] += off
            if e["type"] == "cap" and "id" in e: markers["caps"][e["id"]] = round(e["t"], 3)
            if e["type"] == "sfx": markers["ev"].append([s, e["name"], round(e["t"], 3)])
            if "end" in e: e["end"] = min(e["end"], tl["duration"]) + off
            {"cap": caps, "sfx": sfx, "vo": vo, "chapter": chaps}[e["type"]].append(e)
        lst.append(f"file '{mp4}'"); off += d
    dur = off
    markers["total"] = dur
    json.dump(markers, open(os.path.join(b, "markers.json"), "w"), indent=1)   # chapter / beat / cue times (music fitting)
    open(os.path.join(b, "concat.txt"), "w").write("\n".join(lst) + "\n")
    raw = os.path.join(b, "raw.mp4")
    sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(b, "concat.txt"), "-c", "copy", raw])
    tl_all = {"duration": dur, "theme": theme, "captions": caps, "chapters": chaps, "vo": vo, "sfx": sfx}
    json.dump(tl_all, open(os.path.join(b, "timeline_all.json"), "w"), ensure_ascii=False, indent=1)
    ass = os.path.join(b, "captions.ass"); write_ass(caps, chaps, ass, theme, a.en_subs)
    write_srt(caps, os.path.join(b, "captions.srt"))
    # stems
    n = int(round(dur * SR))
    sf.write(os.path.join(stems, "sfx.wav"), build_sfx(sfx, n, os.path.join(ROOT, "assets", "sfx")), SR, subtype="FLOAT")
    sf.write(os.path.join(stems, "vo.wav"), build_vo(vo, n, os.path.join(b, "vo")), SR, subtype="FLOAT")
    json.dump(mix.activity(vo), open(os.path.join(stems, "vo_activity.json"), "w"))
    ph = os.path.join(stems, "music_placeholder.wav")
    if not os.path.exists(ph) or sf.info(ph).frames != n:
        sf.write(ph, mix.placeholder_pad(n), SR, subtype="FLOAT")
    shutil.copy(os.path.join(b, "timeline_all.json"), os.path.join(stems, "timeline.json"))
    shutil.copy(os.path.join(b, "captions.srt"), os.path.join(stems, "captions.srt"))
    # picture
    pic = os.path.join(stems, "picture.mp4")
    if not a.skip_video or not os.path.exists(pic):
        if theme == "light":
            sys.path.insert(0, LIB)
            plate = os.path.join(ROOT, "assets", "plate_light.png"); band = os.path.join(ROOT, "assets", "caption_band_light.png")
            make_plate_light(plate, "#F4F6FA", "#E8EDF5"); make_caption_band(band)
            finish_light(raw, plate, band, ass, pic, dur)
        else:
            plate = os.path.join(ROOT, "assets", "plate_stars.png")
            if not os.path.exists(plate): make_plate_dark(plate)
            finish_dark(raw, plate, ass, pic, dur)
    outs = mix.render_variants(stems, os.path.join(a.out_dir, a.name), a.music, a.music_start, a.music_db)
    for o in outs: print("DONE", o, f"{dur:.2f}s")

if __name__ == "__main__":
    main()
