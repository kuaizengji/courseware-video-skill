"""Paths + user configuration for the courseware-video toolkit.

Locations (all overridable by environment variables):
  CVS_HOME     install root (default: the folder that contains toolkit/, e.g. ~/courseware-video)
  CVS_MODELS   Kokoro model folder           (default: $CVS_HOME/models)
  CVS_SF2      Salamander Grand Piano .sf2   (default: $CVS_HOME/soundfonts/SalamanderGrandPiano-V3+20200602.sf2)
  CVS_CONFIG   JSON config file              (default: $CVS_HOME/config.json, falling back to toolkit/config.default.json)
  CVS_PROJECT  project folder for outputs    (default: current working directory)

config.json keys (any subset; missing keys fall back to toolkit/config.default.json):
  brand.logo_light / brand.logo_dark  SVG for light / dark themes (relative paths resolve against toolkit/assets/)
  brand.site                          e.g. "www.kuaizengji.com"; "" hides the 'Powered by' line
  brand.powered_by                    full override of the line text (default "Powered by <site>")
  brand.enabled                       false -> no logo / powered-by on the end card
  voice.name / voice.speed / voice.lang   Kokoro voice (default am_michael, 1.03, en-us)
  theme                               "light" | "dark" (DSA_THEME env still wins)
  music.pad                           default bed timbre for the score engine (X2)
"""
import json, os

TOOLKIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CVS_HOME = os.path.abspath(os.environ.get("CVS_HOME") or os.path.dirname(TOOLKIT))
LIB = os.path.join(TOOLKIT, "lib")
MUSIC = os.path.join(TOOLKIT, "music")
ASSETS = os.path.join(TOOLKIT, "assets")
MODELS = os.environ.get("CVS_MODELS") or os.path.join(CVS_HOME, "models")
KOKORO_MODEL = os.path.join(MODELS, "kokoro-v1.0.onnx")
KOKORO_VOICES = os.path.join(MODELS, "voices-v1.0.bin")
SF2 = os.environ.get("CVS_SF2") or os.path.join(CVS_HOME, "soundfonts", "SalamanderGrandPiano-V3+20200602.sf2")
PROJECT = os.path.abspath(os.environ.get("CVS_PROJECT") or os.getcwd())


def _merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config():
    cfg = json.load(open(os.path.join(TOOLKIT, "config.default.json"), encoding="utf-8"))
    user = os.environ.get("CVS_CONFIG") or os.path.join(CVS_HOME, "config.json")
    if os.path.exists(user):
        cfg = _merge(cfg, json.load(open(user, encoding="utf-8")))
    return cfg


CONFIG = load_config()


def asset(p):
    """Resolve a config path: absolute, or relative to toolkit/assets/."""
    return p if not p or os.path.isabs(p) else os.path.join(ASSETS, p)


def powered_by_text():
    b = CONFIG.get("brand", {})
    if not b.get("enabled", True): return ""
    if b.get("powered_by"): return b["powered_by"]
    return f"Powered by {b['site']}" if b.get("site") else ""
