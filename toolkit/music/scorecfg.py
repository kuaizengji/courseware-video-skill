"""Per-episode music parameters for the score engine (score_v4.py).

Every episode should get its OWN key, progression, tempo, motif and bed (SKILL.md section 4). Only the structure
(continuous bed, layers switched per section, near-silences, dead stop, climax on the reveal, piano recap, tonic-major
ending) is fixed in code. Give the parameters as a JSON file (--music-config) and/or CLI flags (flags win):

{
  "bpm": 120,                    # fixed round tempo, 4/4 (bar = 240/bpm s). Never bent.
  "key": "D minor",              # transposes the BUILT-IN material (progression + motif) to this key.
                                 # "X major" uses the relative-minor material (the built-in theme is minor-mode
                                 # with a major ending). Ignored for any part you write yourself (below).
  "pad": "X2",                   # bed timbre: X X1 X2 X3 A B C D (see pads.py)
  "seed": 11,
  "progression": {               # absolute chord symbols (engine/theory.py syntax: Dm, Bbmaj7, Cadd9, G/D, Asus4 ...)
    "intro":   "Dmadd9",         # first 2 bars
    "loop":    ["Dmadd9","Dmadd9","Bbmaj7","Bbmaj7","Gm7","Gm7","Cadd9","Cadd9"],   # 8 bars, 1 chord per bar
    "cadence": ["Asus4","A"],    # the 2 bars before the climax (and the bar before the ending uses cadence[1])
    "ending":  "Dadd9"           # end card (tonic major = Picardy ending)
  },
  "motif": {                     # one melodic idea for the whole video, bars as 'Note:beats' tokens, r = rest
    "pickup": "r:1 A4:1 D5:1 E5:1",
    "theme":  ["F5:3 E5:1", "D5:1 F4:1 Bb4:1 C5:1", ...8 bars, written over loop bars 1-8...],
    "coda":   ["Bb4:3 r:1", "C#5:1 A4:1 D5:1 E5:1", "F#5:3 E5:1", "D5:4", "r:4", "A4:2 D5:2"]
  },
  "sections": [                  # cue sheet: anchor -> section style (anchors: "start", "ch:<num>", "cap:<caption id>")
    ["start","open"], ["ch:1","calm"], ["ch:2","pulse"], ["ch:3","lift"], ["ch:4","calm2"], ["ch:5","code"],
    ["ch:6","code2"], ["ch:7","build"], ["cap:m12","climax"], ["ch:8","recap"], ["cap:e1","end"]
  ],
  "pulse_groove_until": "cap:o6" # in a 'pulse' section the full groove stops at this caption (else start + 9 bars)
}
Styles: open calm pulse lift calm2 code code2 build climax recap end. Required: open, build, climax, recap, end
(climax = the hero reveal; its anchor gets the 0.4 s dead stop before it).
Defaults below = the approved 'Stacks' episode score (D minor, 120 BPM, X2), which reproduces it exactly.
"""
import json, re
from engine import theory as th

DEFAULT = {
    "bpm": 120, "key": "D minor", "pad": "X2", "seed": 11,
    "progression": {"intro": "Dmadd9", "loop": ["Dmadd9", "Dmadd9", "Bbmaj7", "Bbmaj7", "Gm7", "Gm7", "Cadd9", "Cadd9"],
                    "cadence": ["Asus4", "A"], "ending": "Dadd9"},
    "motif": {"pickup": "r:1 A4:1 D5:1 E5:1",
              "theme": ["F5:3 E5:1", "D5:1 F4:1 Bb4:1 C5:1", "D5:3 C5:1", "Bb4:1 D5:1 G5:1 A5:1",
                        "Bb5:3 A5:1", "G5:1 E5:1 F5:1 G5:1", "A5:3 G5:1", "E5:1 A4:1 D5:1 E5:1"],
              "coda": ["Bb4:3 r:1", "C#5:1 A4:1 D5:1 E5:1", "F#5:3 E5:1", "D5:4", "r:4", "A4:2 D5:2"]},
    "sections": [["start", "open"], ["ch:1", "calm"], ["ch:2", "pulse"], ["ch:3", "lift"], ["ch:4", "calm2"],
                 ["ch:5", "code"], ["ch:6", "code2"], ["ch:7", "build"], ["cap:m12", "climax"], ["ch:8", "recap"],
                 ["cap:e1", "end"]],
    "pulse_groove_until": "cap:o6",
}
SHARP = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def key_shift(key):
    """'E minor' -> +2 (relative to the built-in D minor), folded into -5..+6. 'F major' -> relative minor D -> 0."""
    m = re.fullmatch(r"\s*([A-Ga-g][b#]?)\s*(major|minor|maj|min|m)?\s*", key or "D minor")
    if not m: raise ValueError(f"bad key: {key!r} (use e.g. 'E minor', 'G major')")
    pc = th.pc_of(m.group(1)[0].upper() + m.group(1)[1:])
    if (m.group(2) or "minor") in ("major", "maj"): pc = (pc - 3) % 12
    k = (pc - 2) % 12
    return k - 12 if k > 6 else k


def tr_chord(sym, k):
    if not k: return sym
    def f(mm): return SHARP[(th.pc_of(mm.group(0)) + k) % 12]
    m = re.fullmatch(r"([A-G][b#]?)([a-z0-9]*)(?:/([A-G][b#]?))?", sym)
    if not m: raise ValueError(sym)
    out = f(re.match(r".*", m.group(1))) + m.group(2)
    if m.group(3): out += "/" + SHARP[(th.pc_of(m.group(3)) + k) % 12]
    return out


def tr_bar(bar, k):
    if not k: return bar
    out = []
    for tok in bar.split():
        nm, _, d = tok.partition(":")
        out.append(tok if nm == "r" else f"{th.nname(th.note(nm) + k)}:{d}")
    return " ".join(out)


def load(path=None, **over):
    """Merge DEFAULT <- JSON file <- CLI overrides; transpose the built-in parts to `key`."""
    user = json.load(open(path)) if path else {}
    for k_, v in over.items():
        if v is not None: user[k_] = v
    cfg = json.loads(json.dumps(DEFAULT))
    for k_ in ("bpm", "key", "pad", "seed", "sections", "pulse_groove_until"):
        if k_ in user: cfg[k_] = user[k_]
    k = key_shift(cfg["key"])
    prog_u, mot_u = user.get("progression", {}), user.get("motif", {})
    for k_, v in cfg["progression"].items():
        cfg["progression"][k_] = prog_u[k_] if k_ in prog_u else ([tr_chord(c, k) for c in v] if isinstance(v, list) else tr_chord(v, k))
    for k_, v in cfg["motif"].items():
        cfg["motif"][k_] = mot_u[k_] if k_ in mot_u else ([tr_bar(b, k) for b in v] if isinstance(v, list) else tr_bar(v, k))
    P, M = cfg["progression"], cfg["motif"]
    assert len(P["loop"]) == 8 and len(M["theme"]) == 8 and len(P["cadence"]) == 2, "loop/theme need 8 bars, cadence 2"
    for c in P["loop"] + P["cadence"] + [P["intro"], P["ending"]]: th.chord(c)          # validate symbols
    styles = [s for _, s in cfg["sections"]]
    for req in ("open", "build", "climax", "recap", "end"):
        assert req in styles, f"sections must include '{req}'"
    cfg["shift"] = k
    return cfg


def tonic_tones(cfg):
    """Derived tonic-chord pitches for the swells / climax hit / push SFX scale (D minor -> the original numbers)."""
    _, pcs, bpc = th.chord(cfg["progression"]["loop"][0])
    r = th.in_range(bpc, 45, 56)[0]
    third = (pcs[1] - pcs[0]) % 12 if len(pcs) > 1 else 3
    swell = [r, r + 7, r + 12, r + 12 + third, r + 19]
    hit = [r - 12, r - 5, r, r + third, r + 7, r + 12, r + 12 + third]
    pent = [0, 3, 5, 7, 10] if third == 3 else [0, 2, 4, 7, 9]
    penta = [r + 12 + o + 12 * octv for octv in (0, 1) for o in pent]
    return dict(root=r, swell=swell, hit=hit, low=[r - 24, r - 12], penta=penta)
