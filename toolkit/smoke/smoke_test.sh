#!/bin/bash
# End-to-end smoke test: Manim scene with caption (~3-4 s) + 5-s music bed + one TTS line, muxed into one MP4.
# TTS uses Gemini when GEMINI_API_KEY is set, otherwise Kokoro (no key needed).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export CVS_HOME="${CVS_HOME:-$(cd "$HERE/../.." && pwd)}"
PY="$CVS_HOME/venv/bin/python"; MANIM="$CVS_HOME/venv/bin/manim"; TK="$CVS_HOME/toolkit"
W="${SMOKE_DIR:-$CVS_HOME/smoke_run}"
rm -rf "$W"; mkdir -p "$W"; cp "$HERE/script.py" "$HERE/scenes.py" "$W/"
sed -i "s#os.path.join(EP, \"..\", \"lib\")#\"$TK/lib\"#" "$W/scenes.py"
cd "$W"
echo "[1/5] TTS";        "$PY" "$TK/lib/tts.py" . ${SMOKE_TTS_PROVIDER:+--provider $SMOKE_TTS_PROVIDER}
echo "[2/5] Manim";      "$MANIM" -r 1920,1080 --fps 30 --disable_caching scenes.py Smoke > manim.log 2>&1 || { tail -30 manim.log; exit 1; }
VDIR=$(ls -d media/videos/scenes/*/ | head -1)
echo "[3/5] post (captions, picture, stems)"
"$PY" "$TK/lib/post.py" . --name smoke_sfx --stems "$W/stems" --out-dir "$W" --scenes Smoke --video-dir "$VDIR"
echo "[4/5] music bed";  "$PY" "$TK/music/bed.py" --seconds 5 --out "$W/bed.wav"
echo "[5/5] mix + mux";  "$PY" "$TK/lib/mix.py" "$W/stems" --music "$W/bed.wav" --out "$W/smoke"
"$PY" - "$W" <<'PYEOF'
import json, subprocess, sys, os
w = sys.argv[1]; ok = True
for v in ("noVO", "VO"):
    f = os.path.join(w, f"smoke_{v}.mp4")
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", f], capture_output=True, text=True).stdout)
    kinds = sorted(s["codec_type"] for s in j["streams"]); d = float(j["format"]["duration"])
    vs = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    print(f"  {os.path.basename(f)}: {d:.2f}s streams={kinds} {vs['width']}x{vs['height']}")
    ok &= kinds == ["audio", "video"] and d > 2.0
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", os.path.join(w, "smoke_VO.mp4"), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float(r[r.rfind("I:"):].split()[1]); print(f"  loudness VO mix: {I:.1f} LUFS"); ok &= -20 < I < -12
caps = open(os.path.join(w, "build", "captions.srt"), encoding="utf-8").read(); ok &= "安装成功" in caps
prov = json.load(open(os.path.join(w, "build", "vo", "provider.json"))); print("  TTS provider:", prov)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "2.0", "-i", os.path.join(w, "smoke_VO.mp4"), "-frames:v", "1", os.path.join(w, "smoke_frame.png")])
print("SMOKE TEST", "PASSED" if ok else "FAILED", "->", os.path.join(w, "smoke_VO.mp4"))
sys.exit(0 if ok else 1)
PYEOF
