"""Delivery gate: one command, ERROR/WARN levels, exit code 1 on any ERROR (2 on bad usage).

  python $CVS_HOME/toolkit/lib/qa.py gate <video> [--captions a.srt b.ass c.json ...] [--log render.log]
        [--keys DECISIONS.md --ep ID] [--ep-dir ep/<id> [--scenes S1 S2]] [--edgescan]
        [--size 1920x1080] [--fps 30] [--lufs -16] [--forbid word ...] [--sheet out.jpg]

Checks: spec (size/fps/duration/frames) · loudness (integrated within +-0.5 LU of target = OK, +-1 = WARN,
beyond = ERROR; true peak must be < -1 dBTP) · metadata (only title/encoder/brand tags) · render log errors ·
captions (ASCII { } in lines with CJK -> ASS swallows them; courseware-trace words) · key table (same tonic+mode
used twice = ERROR, same tempo = WARN) · optional box-overflow (qa.py boxes) and edge scan (WARN; light teaching
theme only: on dark promo films every frame is flagged) · contact sheet.
ffmpeg runs with -threads 2; run the whole gate under `nice`.

Key table format (a section in DECISIONS.md; one row per video):
  ## Key table
  | id | key | mode | bpm |
  |---|---|---|---|
  | L01 | F# | minor | 120 |
  | B06 | F | lydian | 100 |
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE = [r"\bslides?\b", r"\blectures?\b", r"\blab\s*\d*\b", r"\btutorial\s*\d+\b", r"\bweek\s*\d+\b",
         r"\bhomework\b", r"\bassignment\b", r"课件", r"讲义", r"幻灯片", r"第\s*\d+\s*(讲|周|课)", r"作业"]
ENH = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#", "CB": "B", "FB": "E", "E#": "F", "B#": "C"}
OKTAGS = {"title", "encoder", "major_brand", "minor_version", "compatible_brands", "handler_name", "vendor_id", "language"}
rows = []


def rep(level, name, detail):
    rows.append(level); print(f"{level:6s}{name:10s}{detail}")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def tonic(k):
    k = k.strip().upper().replace("♯", "#").replace("♭", "B")
    k = k[0] + k[1:].replace("FLAT", "B").replace("SHARP", "#").replace("-", "").replace(" ", "")
    return ENH.get(k, k)


def mode(m):
    m = m.strip().lower()
    return {"major": "ionian", "maj": "ionian", "minor": "aeolian", "min": "aeolian", "m": "aeolian"}.get(m, m)


def key_table(path):
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"^## Key table\s*$(.*?)(?=^## |\Z)", txt, re.M | re.S)
    if not m: return None
    out = []
    for line in m.group(1).splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 4 and c[0] and c[0].lower() != "id" and not set(c[0]) <= set("-: "):
            out.append({"id": c[0], "key": c[1], "mode": c[2], "bpm": c[3], "pair": (tonic(c[1]), mode(c[2]))})
    return out


def check_keys(path, ep):
    t = key_table(path)
    if t is None: rep("ERROR", "keys", f"no '## Key table' section in {path}"); return
    mine = [r for r in t if r["id"] == ep] if ep else t
    if ep and not mine: rep("ERROR", "keys", f"{ep} has no row in the key table"); return
    bad = 0
    for r in mine:
        for o in t:
            if o is r or o["id"] == r["id"] or (not ep and o["id"] < r["id"]): continue
            if o["pair"] == r["pair"]:
                bad += 1; rep("ERROR", "keys", f"{r['id']} {r['key']} {r['mode']} clashes with {o['id']} {o['key']} {o['mode']}")
            elif o["bpm"] and o["bpm"] == r["bpm"]:
                rep("WARN", "keys", f"{r['id']} and {o['id']} share tempo {r['bpm']} BPM (keys differ)")
    if not bad: rep("OK", "keys", f"{len(mine)} row(s) checked against {len(t)}: no tonic+mode clash")


def main(argv):
    ap = argparse.ArgumentParser(prog="qa.py gate")
    ap.add_argument("video"); ap.add_argument("--captions", nargs="*", default=[]); ap.add_argument("--log")
    ap.add_argument("--keys"); ap.add_argument("--ep"); ap.add_argument("--ep-dir"); ap.add_argument("--scenes", nargs="*", default=[])
    ap.add_argument("--edgescan", action="store_true"); ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=float, default=None); ap.add_argument("--lufs", type=float, default=-16.0)
    ap.add_argument("--forbid", nargs="*", default=[]); ap.add_argument("--sheet")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.video): print("usage error: video not found:", a.video); return 2

    pr = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames:format=duration:format_tags",
                         "-of", "json", a.video]).stdout or "{}")
    v = next((s for s in pr.get("streams", []) if s["codec_type"] == "video"), None)
    au = next((s for s in pr.get("streams", []) if s["codec_type"] == "audio"), None)
    if not v: rep("ERROR", "spec", "no video stream"); return 1
    num, den = map(int, v["r_frame_rate"].split("/")); fps = num / den; dur = float(pr["format"]["duration"])
    size = f"{v['width']}x{v['height']}"
    rep("OK" if size == a.size else "ERROR", "spec", f"{v['codec_name']} {size} (want {a.size}) @ {fps:.3f} fps, {dur:.2f} s, frames {v.get('nb_frames', '?')}, audio {au['codec_name'] if au else 'NONE'}")
    if a.fps and abs(fps - a.fps) > 0.01: rep("ERROR", "spec", f"fps {fps:.3f} != {a.fps}")
    if not au: rep("ERROR", "audio", "no audio stream")
    else:
        r = run(["ffmpeg", "-hide_banner", "-nostats", "-threads", "2", "-i", a.video, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
        s = r[r.rfind("Summary"):]
        I = re.search(r"I:\s+(-?[\d.]+) LUFS", s); P = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", s)
        if not I: rep("ERROR", "loudness", "could not measure")
        else:
            i = float(I.group(1)); d = abs(i - a.lufs)
            rep("OK" if d <= 0.5 else "WARN" if d <= 1 else "ERROR", "loudness", f"{i:.1f} LUFS (target {a.lufs:g})")
            p = float(P.group(1)) if P else 0.0
            rep("OK" if p < -1 else "ERROR", "truepeak", f"{p:.1f} dBTP (must be < -1)")
    extra = {k: v for k, v in pr["format"].get("tags", {}).items() if k.lower() not in OKTAGS}
    rep("ERROR" if extra else "OK", "metadata", f"extra tags {extra}" if extra else "only title/encoder/brand tags")
    if a.log:
        L = open(a.log, encoding="utf-8", errors="replace").read().splitlines()
        e = [l for l in L if re.search(r"Traceback|\bError\b|ERROR|Exception", l)]
        rep("ERROR" if e else "OK", "renderlog", f"{len(e)} error line(s)" + (f": {e[0][:100]}" if e else ""))
    pats = [re.compile(p, re.I) for p in TRACE + [re.escape(w) for w in a.forbid]]
    for c in a.captions:
        txt = open(c, encoding="utf-8").read(); ass = c.lower().endswith((".ass", ".ssa"))
        br, tr = [], []
        for n, line in enumerate(txt.splitlines(), 1):
            body = line.split(",", 9)[-1] if ass and line.startswith("Dialogue:") else line
            if ass: body = re.sub(r"\{\\[^}]*\}", "", body)
            if re.search(r"[\u4e00-\u9fff]", body) and re.search(r"[{}]", body): br.append(n)
            if not (ass and not line.startswith("Dialogue:")) and any(p.search(body) for p in pats): tr.append((n, body.strip()[:70]))
        rep("ERROR" if br else "OK", "braces", f"{os.path.basename(c)}: " + (f"ASCII {{ }} on CJK lines {br[:8]} -> use full-width ｛ ｝" if br else "none"))
        rep("ERROR" if tr else "OK", "trace", f"{os.path.basename(c)}: " + (f"{len(tr)} hit(s), first line {tr[0][0]}: {tr[0][1]}" if tr else "no courseware-trace words"))
    if a.keys: check_keys(a.keys, a.ep)
    if a.ep_dir and not os.path.isfile(os.path.join(HERE, "boxcheck.py")):
        rep("WARN", "boxes", "boxcheck.py not bundled with this toolkit: check text-in-box overflow by eye on the contact sheet")
    elif a.ep_dir:
        r = run([sys.executable, os.path.join(HERE, "qa.py"), "boxes", a.ep_dir, *a.scenes])
        out = [l for l in r.stdout.splitlines() if l.startswith(("OUT", "ERR"))]
        rep("ERROR" if out or r.returncode else "OK", "boxes", f"{len(out)} text-outside-box finding(s)" + (f": {out[0][:100]}" if out else "") + (f" (exit {r.returncode})" if r.returncode else ""))
    if a.edgescan:
        r = run([sys.executable, os.path.join(HERE, "edgescan.py"), a.video]); last = (r.stdout.strip().splitlines() or ["?"])[-1]
        rep("OK" if last.startswith("0 ranges") else "WARN", "edgescan", last + " (look at each range; cards 40-60 px from the edge can be fine)")
    if a.sheet:
        r = run([sys.executable, os.path.join(HERE, "qa.py"), "sheet", a.video, a.sheet, "4", "4"])
        rep("OK" if r.returncode == 0 else "WARN", "sheet", a.sheet + " -> open it and look at every frame")
    ne, nw = rows.count("ERROR"), rows.count("WARN")
    print(f"GATE {'FAIL' if ne else 'PASS'}: {ne} ERROR, {nw} WARN")
    return 1 if ne else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
