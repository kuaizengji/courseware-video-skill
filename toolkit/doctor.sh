#!/usr/bin/env bash
# Doctor: check the courseware-video toolchain WITHOUT installing anything.
#   bash $CVS_HOME/toolkit/doctor.sh      -> OK / MISSING / WARN per item, with the fix; exit 1 if anything is MISSING
# Run it at the start of a session, after a machine restart, or when a script fails oddly; then re-run install.sh
# (idempotent) only if something is MISSING.
set -u
CVS_HOME="${CVS_HOME:-$HOME/courseware-video}"
miss=0
ok()   { printf 'OK      %-20s %s\n' "$1" "$2"; }
warn() { printf 'WARN    %-20s %s\n' "$1" "$2"; }
no()   { printf 'MISSING %-20s %s\n%29s-> %s\n' "$1" "$2" "" "$3"; miss=1; }
FIX="bash install.sh   (from the repo; CVS_HOME=$CVS_HOME)"

[ -d "$CVS_HOME/toolkit" ] && ok "CVS_HOME" "$CVS_HOME" || no "CVS_HOME" "$CVS_HOME/toolkit not found" "$FIX"
if [ -f "$CVS_HOME/apt-packages.txt" ] && command -v dpkg-query >/dev/null; then
  M=$(grep -vE '^\s*(#|$)' "$CVS_HOME/apt-packages.txt" | while read -r p; do dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || printf '%s ' "$p"; done)
  [ -z "$M" ] && ok "apt packages" "all present" || no "apt packages" "$M" "$FIX"
else warn "apt packages" "not a Debian/Ubuntu system or apt-packages.txt missing: check by hand"; fi
for b in ffmpeg ffprobe fluidsynth pdftoppm soffice; do
  command -v $b >/dev/null && ok "$b" "$(command -v $b)" || no "$b" "not on PATH" "$FIX"; done
V="$CVS_HOME/venv/bin/python"
if [ -x "$V" ]; then
  "$V" -c 'import manim, kokoro_onnx, soundfile, pyloudnorm, pretty_midi, scipy, librosa' 2>/dev/null \
    && ok "venv" "$("$V" -c 'import manim; print("manim", manim.__version__)' 2>/dev/null)" \
    || no "venv" "python deps fail to import" "$FIX"
else no "venv" "$CVS_HOME/venv missing" "$FIX"; fi
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "$CVS_HOME/models/$f" ] && ok "model $f" "present" || no "model $f" "missing" "$FIX"; done
ls "$CVS_HOME"/soundfonts/*.sf2 >/dev/null 2>&1 && ok "Salamander sf2" "present" || no "Salamander sf2" "missing" "$FIX"
command -v fc-list >/dev/null && fc-list | grep -qi 'Noto Sans CJK' && ok "CJK font" "Noto Sans CJK" || no "CJK font" "missing" "$FIX"
[ -f "$CVS_HOME/env.sh" ] && ok "env.sh" "source $CVS_HOME/env.sh" || no "env.sh" "missing" "$FIX"
command -v latex >/dev/null && ok "latex (optional)" "MathTex available" || warn "latex (optional)" "only needed for Manim MathTex formulas"
free_gb=$(df -Pk "$CVS_HOME" 2>/dev/null | awk 'NR==2{print int($4/1048576)}')
[ "${free_gb:-0}" -ge 10 ] && ok "disk" "${free_gb} GB free" || warn "disk" "${free_gb:-?} GB free (renders need ~10 GB)"
[ $miss = 0 ] && echo "doctor: all OK" || echo "doctor: something is MISSING (see -> lines)"
exit $miss
