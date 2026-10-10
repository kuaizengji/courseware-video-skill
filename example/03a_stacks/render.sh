#!/bin/bash
# Stacks (example episode) - full pipeline, as used for the approved version:
#   VO (Gemini if GEMINI_API_KEY is set, else Kokoro am_michael) -> Manim scenes (1080p30, parallel)
#   -> post (picture + captions + stems) -> bar grid -> score (music.json) -> mux noVO / VO -> QA contact sheet.
# Usage: bash render.sh            (Q="-ql" for a fast low-res draft, J=<parallel jobs>)
set -e
cd "$(dirname "$0")"
CVS_HOME=${CVS_HOME:-$(cd ../.. && pwd)}; export CVS_HOME
PY=$CVS_HOME/venv/bin/python; MANIM=$CVS_HOME/venv/bin/manim; TK=$CVS_HOME/toolkit
NAME=${NAME:-stacks}; OUT=${OUT:-$PWD/out}; STEMS=$OUT/${NAME}_stems
SCENES="S00_Title S01_Definition S02_Operations S03_Applications S04_Choice S05_Implementation S06_Display S07_Demo S08_Summary"
Q=${Q:-"-r 1920,1080 --fps 30"}
J=${J:-$(nproc)}
mkdir -p build/logs "$OUT"
$PY $TK/lib/tts.py .                                   # cached; only changed lines are re-synthesised
echo $SCENES | tr ' ' '\n' | xargs -P $J -I{} sh -c "$MANIM $Q --disable_caching scenes.py {} > build/logs/{}.log 2>&1 && echo rendered {} || (echo FAILED {}; tail -20 build/logs/{}.log; exit 1)"
VDIR=$(ls -d media/videos/scenes/*/ | head -1)
$PY $TK/lib/post.py . --name ${NAME}_sfxonly --stems "$STEMS" --out-dir "$OUT" --scenes $SCENES --video-dir "$VDIR"
REVEAL=$($PY -c "import json;print(json.load(open('music.json')).get('reveal_caption','m12'))")
BPM=$($PY -c "import json;print(json.load(open('music.json')).get('bpm',120))")
$PY $TK/music/grid_03a.py "$STEMS/timeline.json" --bpm $BPM --reveal $REVEAL --out build/grid.json
$PY $TK/music/score_v4.py --stems "$STEMS" --grid build/grid.json --outdir build/score --music-config music.json
for v in noVO VO; do
  ffmpeg -y -v error -i build/score/mix_$v.wav -ar 48000 -c:a aac -b:a 192k build/score/mix_$v.m4a
  $PY -c "import sys; sys.path.insert(0,'$TK/lib'); import mix; mix.mux('$STEMS/picture.mp4','build/score/mix_$v.m4a','$OUT/${NAME}_$v.mp4', title='Stacks')"
  echo "wrote $OUT/${NAME}_$v.mp4"
done
$PY $TK/lib/qa.py sheet "$OUT/${NAME}_VO.mp4" "$OUT/${NAME}_contact.png" 4 4
$PY $TK/lib/qa.py loud "$OUT/${NAME}_VO.mp4" || true
