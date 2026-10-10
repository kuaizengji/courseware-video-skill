#!/usr/bin/env bash
# courseware-video toolkit installer (idempotent; safe to re-run).
#   bash install.sh                         -> installs into $CVS_HOME (default $HOME/courseware-video)
#   CVS_HOME=/some/dir bash install.sh      -> installs elsewhere
# Env switches: CVS_SKIP_APT=1  CVS_SKIP_SMOKE=1  CVS_SF2=/path/to/existing.sf2 (reuse instead of downloading)
# Needs: Debian/Ubuntu with sudo (for apt), internet. CPU only. No API keys required
# (Gemini TTS is optional: export GEMINI_API_KEY at run time; it is never written to disk).
set -euo pipefail
PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CVS_HOME="${CVS_HOME:-$HOME/courseware-video}"
log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

KOKORO_BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_ONNX_SHA="7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"     # kokoro-v1.0.onnx (325,532,387 B)
KOKORO_VOICES_SHA="bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"   # voices-v1.0.bin  (28,214,398 B)
SAL_URL="https://freepats.zenvoid.org/Piano/SalamanderGrandPiano/SalamanderGrandPiano-SF2-V3%2B20200602.tar.xz"
SAL_SHA="15edb061d7ba60d58332f72dba8f8ce40988048cc703f935e6320f37d650e213"             # tar.xz (310,397,984 B)
SAL_SF2_NAME="SalamanderGrandPiano-V3+20200602.sf2"

# ---------------------------------------------------------------- 1. files
log "1/7 toolkit files -> $CVS_HOME"
mkdir -p "$CVS_HOME"
if [ "$(cd "$CVS_HOME" && pwd)" != "$PKG" ]; then
  for f in toolkit example SKILL.md README.md THIRD_PARTY_LICENSES.md LICENSE requirements.txt constraints.txt apt-packages.txt install.sh; do
    [ -e "$PKG/$f" ] || continue
    rm -rf "$CVS_HOME/$f.new"; cp -a "$PKG/$f" "$CVS_HOME/$f.new"; rm -rf "$CVS_HOME/$f"; mv "$CVS_HOME/$f.new" "$CVS_HOME/$f"
  done
fi
[ -f "$CVS_HOME/config.json" ] || cp "$CVS_HOME/toolkit/config.default.json" "$CVS_HOME/config.json"
mkdir -p "$CVS_HOME/models" "$CVS_HOME/soundfonts"

# ---------------------------------------------------------------- 2. apt
log "2/7 system packages"
mapfile -t PKGS < <(grep -vE '^\s*(#|$)' "$CVS_HOME/apt-packages.txt")
MISSING=()
for p in "${PKGS[@]}"; do dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || MISSING+=("$p"); done
if [ ${#MISSING[@]} -eq 0 ]; then echo "all ${#PKGS[@]} packages present"
elif [ "${CVS_SKIP_APT:-0}" = 1 ]; then echo "WARNING: missing (CVS_SKIP_APT=1, not installing): ${MISSING[*]}"
else
  SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"
  echo "installing: ${MISSING[*]}"
  $SUDO apt-get update -qq
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq --no-install-recommends "${MISSING[@]}"
fi
for b in ffmpeg ffprobe fluidsynth pdftoppm soffice; do command -v $b >/dev/null || echo "WARNING: $b not on PATH"; done
command -v ffmpeg >/dev/null && command -v fluidsynth >/dev/null || die "ffmpeg and fluidsynth are required"

# ---------------------------------------------------------------- 3. venv + pip
log "3/7 Python venv ($CVS_HOME/venv)"
PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
[ "$PYV" = "3.13" ] || echo "NOTE: pins were tested on Python 3.13; you have $PYV - pip may pick other wheels"
[ -x "$CVS_HOME/venv/bin/python" ] || python3 -m venv "$CVS_HOME/venv"
"$CVS_HOME/venv/bin/python" -m pip install -q --upgrade pip
if [ "$PYV" = "3.13" ]; then
  "$CVS_HOME/venv/bin/pip" install -q -r "$CVS_HOME/requirements.txt" -c "$CVS_HOME/constraints.txt"
else
  "$CVS_HOME/venv/bin/pip" install -q -r "$CVS_HOME/requirements.txt"
fi
"$CVS_HOME/venv/bin/python" -c "import manim, kokoro_onnx, soundfile, pyloudnorm, pretty_midi, scipy, librosa, cv2, cairosvg, pptx, docx; print('python deps OK, manim', manim.__version__)"

# ---------------------------------------------------------------- 4. models / soundfont
fetch() {  # url dest sha256
  local url="$1" dest="$2" sha="$3"
  if [ -f "$dest" ] && echo "$sha  $dest" | sha256sum -c --quiet - 2>/dev/null; then echo "ok (cached) $(basename "$dest")"; return; fi
  echo "downloading $(basename "$dest") ..."
  curl -fsSL --retry 5 --retry-delay 5 -C - -o "$dest.part" "$url" || { rm -f "$dest.part"; curl -fsSL --retry 5 -o "$dest.part" "$url"; }
  echo "$sha  $dest.part" | sha256sum -c --quiet - || { rm -f "$dest.part"; die "checksum mismatch for $url"; }
  mv "$dest.part" "$dest"; echo "ok $(basename "$dest")"
}
log "4/7 Kokoro TTS model (official kokoro-onnx release model-files-v1.0)"
fetch "$KOKORO_BASE/kokoro-v1.0.onnx" "$CVS_HOME/models/kokoro-v1.0.onnx" "$KOKORO_ONNX_SHA"
fetch "$KOKORO_BASE/voices-v1.0.bin"  "$CVS_HOME/models/voices-v1.0.bin"  "$KOKORO_VOICES_SHA"

log "5/7 Salamander Grand Piano SF2 (FreePats, CC BY 3.0, ~1.27 GB unpacked)"
SF2="$CVS_HOME/soundfonts/$SAL_SF2_NAME"
if [ -n "${CVS_SF2:-}" ] && [ -f "$CVS_SF2" ] && [ "$CVS_SF2" != "$SF2" ]; then
  ln -sf "$CVS_SF2" "$SF2"; echo "linked existing $CVS_SF2"
elif [ -s "$SF2" ]; then echo "ok (cached) $SAL_SF2_NAME"
else
  fetch "$SAL_URL" "$CVS_HOME/soundfonts/salamander.tar.xz" "$SAL_SHA"
  tar -xJf "$CVS_HOME/soundfonts/salamander.tar.xz" -C "$CVS_HOME/soundfonts" --strip-components=1
  rm -f "$CVS_HOME/soundfonts/salamander.tar.xz"
  [ -s "$SF2" ] || die "SF2 not found after extraction"
fi
cp -f "$CVS_HOME/toolkit/music/SALAMANDER_README.txt" "$CVS_HOME/soundfonts/" 2>/dev/null || true
unset CVS_SF2   # from here on the toolkit uses $CVS_HOME/soundfonts

# ---------------------------------------------------------------- 6. fonts
log "6/7 fonts"
need_font() { fc-list ":family=$1" family | grep -q . ; }
FDIR="$HOME/.local/share/fonts/courseware-video"
for fam in "Inter:Inter" "JetBrains Mono:JetBrainsMono" "Cormorant Garamond:CormorantGaramond"; do
  name="${fam%%:*}"; dir="${fam##*:}"
  if need_font "$name"; then echo "ok $name"; else mkdir -p "$FDIR"; cp "$CVS_HOME/toolkit/assets/fonts/$dir/"*.ttf "$FDIR/"; echo "installed $name -> $FDIR"; fi
done
fc-cache -f >/dev/null 2>&1 || true
need_font "Noto Serif CJK SC" || die "font 'Noto Serif CJK SC' missing (apt package fonts-noto-cjk)"
need_font "Inter" && need_font "JetBrains Mono" && need_font "Cormorant Garamond" || die "bundled fonts not visible to fontconfig"
echo "fonts OK"

# ---------------------------------------------------------------- 7. smoke test
cat > "$CVS_HOME/env.sh" <<ENV
# source this before using the toolkit:  source $CVS_HOME/env.sh
export CVS_HOME="$CVS_HOME"
export PATH="\$CVS_HOME/venv/bin:\$PATH"
ENV
if [ "${CVS_SKIP_SMOKE:-0}" = 1 ]; then log "7/7 smoke test skipped (CVS_SKIP_SMOKE=1)"
else
  log "7/7 smoke test (TTS: $( [ -n "${GEMINI_API_KEY:-}" ] && echo 'Gemini, Kokoro fallback' || echo 'Kokoro - no GEMINI_API_KEY' ))"
  bash "$CVS_HOME/toolkit/smoke/smoke_test.sh"
fi
log "done. CVS_HOME=$CVS_HOME   (source $CVS_HOME/env.sh)"
