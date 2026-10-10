"""
DSA explainer series - shared Manim style library.
Cinematic dark-navy look: thin cyan lines, gold accent for the key idea, crimson for errors.
Glow/bloom, star dust, vignette and grain are added in post (lib/post.py); this file only
draws clean vector content on a flat BG; post adds the theme background treatment.

Captions are NOT drawn here: DSAScene.cap() records them into a timeline JSON which
post.py turns into an ASS subtitle track (bilingual, bottom-centre). Keep animated content
above SAFE_BOTTOM (y > -2.55) so it never collides with captions.
"""
from manim import *
import json, os, re, contextlib, html, math

# ---------------- theme ----------------
# All colours / background / glow parameters live here so a series can swap themes
# (env DSA_THEME=light|dark; default light). Scenes import the module-level names below.
from dataclasses import dataclass, field
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvs_config as CVS

@dataclass(frozen=True)
class Theme:
    name: str
    bg: str            # flat Manim background (post adds gradient / vignette / texture)
    ink: str           # main text
    soft: str          # secondary text
    dim: str           # tertiary text / captions of figures
    faint: str         # hairlines, empty slots
    accent: str        # primary accent (lines, cells)  [was CYAN]
    accent_d: str      # muted accent (table rules)
    gold: str          # highlight accent (top marker, key ideas)
    hot: str           # brightest sweep / spark colour
    crimson: str
    green: str
    panel: str         # light card fill (tags, UML)
    panel_e: str       # card edge
    cell_fill: str
    cell_fill_op: float
    code_bg: str       # code / console card (kept dark for readability)
    code_edge: str
    code_ink: str
    code_hl: str       # highlight bar on the code card
    halo_op: tuple     # (wide, narrow) halo stroke opacities
    shadow_op: float   # drop-shadow opacity (0 = none)
    dust_colors: tuple
    dust_op: tuple
    # post-processing (lib/post.py)
    post: dict = field(default_factory=dict)

DARK = Theme("dark", bg="#05070d", ink="#E9EDF5", soft="#AEB8CA", dim="#5E6A80", faint="#2A3346",
             accent="#63D2FF", accent_d="#2B6E8E", gold="#F3C46A", hot="#FFFFFF", crimson="#FF4D5E", green="#7EE0B5",
             panel="#0B1222", panel_e="#1C2A44", cell_fill="#0E1A30", cell_fill_op=0.55,
             code_bg="#0B1222", code_edge="#1C2A44", code_ink="#E9EDF5", code_hl="#F3C46A",
             halo_op=(0.06, 0.14), shadow_op=0.0, dust_colors=("#AEB8CA", "#63D2FF", "#F3C46A"), dust_op=(0.35, 0.75),
             post=dict(mode="dark"))
LIGHT = Theme("light", bg="#F4F6FA", ink="#1B2440", soft="#46536F", dim="#6B7895", faint="#C3CCDC",
              accent="#2F55D4", accent_d="#8EA2D8", gold="#B5770C", hot="#FFB020", crimson="#D3263A", green="#1E9E6A",
              panel="#FFFFFF", panel_e="#C9D3E6", cell_fill="#FFFFFF", cell_fill_op=0.94,
              code_bg="#141B2E", code_edge="#2A3654", code_ink="#E9EDF5", code_hl="#F3C46A",
              halo_op=(0.07, 0.16), shadow_op=0.10, dust_colors=("#8C9AB8", "#2F55D4", "#C98A12"), dust_op=(0.22, 0.5),
              post=dict(mode="light", grad=("#F4F6FA", "#E8EDF5")))
THEME = {"light": LIGHT, "dark": DARK}[os.environ.get("DSA_THEME", CVS.CONFIG.get("theme", "light"))]

BG, INK, SOFT, DIM, FAINT = THEME.bg, THEME.ink, THEME.soft, THEME.dim, THEME.faint
CYAN, CYAN_D, GOLD, HOT, CRIMSON, GREEN = THEME.accent, THEME.accent_d, THEME.gold, THEME.hot, THEME.crimson, THEME.green
AMBER = GOLD
PANEL, PANEL_E = THEME.panel, THEME.panel_e
CODE_BG, CODE_EDGE, CODE_INK, CODE_HL = THEME.code_bg, THEME.code_edge, THEME.code_ink, THEME.code_hl

def shadow(mob, dx=0.05, dy=-0.08, op=None):
    """Soft drop shadow (two stacked translucent copies) - gives depth on the light theme."""
    op = THEME.shadow_op if op is None else op
    g = VGroup()
    if op <= 0: return g
    for k, o in ((1.0, op * 0.45), (0.5, op * 0.7)):
        c = mob.copy().set_stroke(width=0).set_fill("#0A1230", opacity=o)
        c.scale([1 + 0.03 * k / max(mob.width, 0.1) * 4, 1 + 0.03 * k / max(mob.height, 0.1) * 4, 1]).shift([dx * (1 + k), dy * (1 + k), 0])
        g.add(c)
    return g

ZH   = "Noto Serif CJK SC"
EN   = "Cormorant Garamond"
MONO = "JetBrains Mono"

SAFE_BOTTOM = -2.55          # nothing animated below this (captions live there)
config.background_color = BG

# ---------------- text helpers ----------------
def esc(s): return html.escape(s, quote=False)

def zh(s, size=40, color=INK, weight=NORMAL, **kw):
    return Text(s, font=ZH, font_size=size, color=color, weight=weight, **kw)

def en(s, size=30, color=SOFT, italic=True, weight=NORMAL, **kw):
    return Text(s, font=EN, font_size=size, color=color, slant=ITALIC if italic else NORMAL, weight=weight, **kw)

def spaced(s, size=20, color=SOFT, spacing=2.2, font=EN, italic=False):
    """Letter-spaced text (Pango letter_spacing; `spacing` ~ em fraction*10)."""
    ls = int(spacing * 1024 * size / 20)
    st = ' font_style="italic"' if italic else ''
    return MarkupText(f'<span letter_spacing="{ls}"{st}>{esc(s)}</span>', font=font, font_size=size, color=color)

def mono(s, size=24, color=INK):
    return MarkupText(f'<span font_features="liga=0,calt=0">{esc(s)}</span>', font=MONO, font_size=size, color=color)

def read_time(zh_text, extra=0.0, cps=6.0, beat=0.4, minimum=1.8):
    """Seconds a caption must stay up: ~6 CJK chars/s + a short beat; latin letters count 1/3."""
    cjk = len(re.findall(r'[\u3400-\u9fff\uff00-\uffef\u3000-\u303f]', zh_text))
    lat = len(re.findall(r'[A-Za-z0-9\-\+\[\]\(\)\.=]', zh_text))
    return max(minimum, (cjk + lat / 3.0) / cps + beat + extra)

# ---------------- Java code highlighting ----------------
JAVA_KW = r'\b(public|static|void|new|return|if|for|int|double|boolean|class|null|this)\b'
JAVA_TYPE = r'\b(Double|String|Stack|System)\b'
def java_markup(line):
    out, i = [], 0
    pat = re.compile(r'("(?:[^"\\]|\\.)*")|' + JAVA_KW + '|' + JAVA_TYPE + r'|(-?\b\d+(?:\.\d+)?\b)')
    for m in pat.finditer(line):
        out.append(esc(line[i:m.start()]))
        tok = esc(m.group(0))
        if m.group(1):   col = "#9FD8A8"       # string
        elif m.group(2): col = "#7FB8FF"       # keyword
        elif m.group(3): col = "#C9A6FF"       # type
        else:            col = "#F3C46A"       # number
        out.append(f'<span foreground="{col}">{tok}</span>')
        i = m.end()
    out.append(esc(line[i:]))
    return ''.join(out)


def mono_row(body, size, x_left, baseline_y, cw, color=INK, java=True):
    """Monospace line placed on a baseline grid (x_left = start of column 0 of `body`).
    Uses an 'x'-prefixed reference render to remove per-glyph ink offsets."""
    mk = java_markup(body) if java else esc(body)
    t = MarkupText(f'<span font_features="liga=0,calt=0">{mk}</span>', font=MONO, font_size=size, color=color)
    ref = MarkupText(f'<span font_features="liga=0,calt=0">x{esc(body)}</span>', font=MONO, font_size=size)
    g0, r0, r1 = t.submobjects[0], ref.submobjects[0], ref.submobjects[1]
    rel_x = r1.get_left()[0] - r0.get_left()[0] - cw
    rel_y = r1.get_center()[1] - r0.get_bottom()[1]
    t.shift(RIGHT * (x_left + rel_x - g0.get_left()[0]) + UP * (baseline_y + rel_y - g0.get_center()[1]))
    return t

class CodePanel(VGroup):
    """Dark rounded panel with verbatim code lines. The highlight bar is a separate
    mobject (self.hl) kept between panel and text via z_index."""
    def __init__(self, lines, size=22, title=None, line_h=None, pad=0.32, min_width=0, **kw):
        super().__init__(**kw)
        self.cw = mono("M" * 40, size).width / 39.6
        self.lh = line_h or size * 0.0165
        self.rows = []
        self.lines = list(lines)
        body_w = max([len(ln.rstrip()) for ln in lines] + [1]) * self.cw
        w = max(body_w + 2 * pad, min_width)
        h = len(lines) * self.lh + 1.6 * pad
        self.box = RoundedRectangle(width=w, height=h, corner_radius=0.16,
                                    fill_color=CODE_BG, fill_opacity=0.97,
                                    stroke_color=CODE_EDGE, stroke_width=1.6)
        self.box.z_index = 0
        self.shadow = shadow(self.box)
        self.add(self.shadow)
        x0 = -w / 2 + pad
        top_y = h / 2 - 0.8 * pad - self.lh * 0.5
        self.ys = []
        for k, ln in enumerate(lines):
            y = top_y - k * self.lh
            self.ys.append(y)
            ind = len(ln) - len(ln.lstrip(' ')); body = ln.strip(' ')
            if body: r = mono_row(body, size, x0 + ind * self.cw, y - size * 0.0045, self.cw, CODE_INK)
            else: r = VectorizedPoint([x0, y, 0])
            r.z_index = 2
            self.rows.append(r)
        self.code = VGroup(*self.rows)
        self.add(self.box, self.code)
        # invisible anchors for line centres (move with the panel)
        self.anchors = VGroup(*[Dot([0, y, 0], radius=0.001).set_opacity(0) for y in self.ys])
        self.add(self.anchors)
        if title:
            self.title = spaced(title, size=13, color=SOFT, spacing=2.2, font=MONO)
            self.title.next_to(self.box, UP, buff=0.12, aligned_edge=LEFT).shift(RIGHT * 0.1)
            self.add(self.title)
        self.hl = None

    def line_y(self, i): return self.anchors[i].get_center()[1]

    def _bar(self, i, j, color):
        y0, y1 = self.line_y(i), self.line_y(j)
        b = RoundedRectangle(width=self.box.width - 0.14, height=abs(y0 - y1) + self.lh * 1.02, corner_radius=0.06,
                             fill_color=color, fill_opacity=0.17, stroke_width=0)
        b.move_to([self.box.get_center()[0], (y0 + y1) / 2, 0])
        acc = Rectangle(width=0.05, height=b.height * 0.86, fill_color=color, fill_opacity=1, stroke_width=0)
        acc.move_to(b.get_left() + RIGHT * 0.05)
        g = VGroup(b, acc); g.z_index = 1
        for m in g: m.z_index = 1
        return g

    def highlight(self, i, j=None, color=CODE_HL, run_time=0.4):
        """Animation sliding (or creating) the highlight bar to line i (..j), with a light glint."""
        nb = self._bar(i, i if j is None else j, color)
        glint = Line(nb[0].get_left(), nb[0].get_right(), stroke_color=color, stroke_width=3)
        glint.move_to(nb[0].get_bottom() + UP * 0.012); glint.z_index = 3
        g = ShowPassingFlash(glint, time_width=0.5, run_time=run_time * 1.6)
        if self.hl is None:
            self.hl = nb
            return AnimationGroup(FadeIn(nb, scale=0.98, run_time=run_time), g)
        return AnimationGroup(Transform(self.hl, nb, run_time=run_time, rate_func=rate_functions.ease_in_out_cubic), g)

    def token(self, i, sub, nth=0):
        """Glyph sub-mobject(s) of substring `sub` in line i (for fly-out effects)."""
        body = self.lines[i].strip(' ')
        k = -1
        for _ in range(nth + 1): k = body.index(sub, k + 1)
        g0 = len(body[:k].replace(' ', '')); n = len(sub.replace(' ', ''))
        return VGroup(*self.rows[i].submobjects[g0:g0 + n])

    def unhighlight(self, run_time=0.3):
        hl, self.hl = self.hl, None
        return FadeOut(hl, run_time=run_time)


class Console(VGroup):
    """Terminal-like output panel; lines appended top-down. With max_lines set, older
    lines scroll up and fade out (keeps the panel small)."""
    def __init__(self, width=4.6, height=4.4, size=19, title="OUTPUT", max_lines=None, **kw):
        super().__init__(**kw)
        self.size = size
        self.lh = size * 0.0158
        self.max_lines = max_lines
        self.box = RoundedRectangle(width=width, height=height, corner_radius=0.16,
                                    fill_color=CODE_BG, fill_opacity=0.97,
                                    stroke_color=CODE_EDGE, stroke_width=1.6)
        self.title = spaced(title, size=13, color=SOFT, spacing=2.4, font=MONO)
        self.title.next_to(self.box, UP, buff=0.12, aligned_edge=LEFT).shift(RIGHT * 0.1)
        self.add(shadow(self.box), self.box, self.title)
        self.cw = mono("M" * 40, size).width / 39.6
        self.n = 0
        self.lines = VGroup(); self.add(self.lines)
        self.visible = []

    def make_line(self, s, color=None, row=None):
        color = color or CODE_INK
        ind = len(s) - len(s.lstrip(' ')); body = s.strip(' ')
        r = self.n if row is None else row
        x0 = self.box.get_left()[0] + 0.25 + ind * self.cw
        y = self.box.get_top()[1] - 0.32 - r * self.lh
        if row is None: self.n += 1
        if not body: return VectorizedPoint([x0, y, 0])
        return mono_row(body, self.size, x0, y - self.size * 0.0045, self.cw, color, java=False)

    def print(self, s, color=None, run_time=0.35):
        if self.max_lines and len(self.visible) >= self.max_lines:
            t = self.make_line(s, color, row=self.max_lines - 1)
            old = self.visible.pop(0)
            anims = [FadeOut(old, shift=UP * self.lh)] + [m.animate.shift(UP * self.lh) for m in self.visible]
            self.visible.append(t); self.lines.add(t)
            return AnimationGroup(*anims, self._type(t), run_time=run_time)
        row = len(self.visible) if self.max_lines else None
        t = self.make_line(s, color, row=row)
        self.visible.append(t); self.lines.add(t)
        return AnimationGroup(self._type(t), run_time=run_time)

    @staticmethod
    def _type(t):
        """Type-on: glyphs appear left to right."""
        if not t.submobjects: return FadeIn(t)
        return LaggedStart(*[FadeIn(g, shift=RIGHT * 0.03) for g in t.submobjects], lag_ratio=0.5 / max(1, len(t.submobjects)) * 4)


# ---------------- data-structure elements ----------------
def glow_stroke(mob, color, widths=(10, 5), opacities=None):
    opacities = opacities or THEME.halo_op
    """Cheap vector halo: copies with wide translucent strokes behind `mob`."""
    halo = VGroup()
    for w, o in zip(widths, opacities):
        c = mob.copy().set_fill(opacity=0).set_stroke(color, width=w, opacity=o)
        halo.add(c)
    return halo

class Cell(VGroup):
    def __init__(self, label, w=1.5, h=0.62, color=CYAN, text_color=INK, size=28, font="mono", fill=None):
        super().__init__()
        fill = THEME.cell_fill_op if fill is None else fill
        self.rect = RoundedRectangle(width=w, height=h, corner_radius=0.12,
                                     fill_color=THEME.cell_fill, fill_opacity=fill,
                                     stroke_color=color, stroke_width=2.2)
        self.halo = glow_stroke(self.rect, color)
        if isinstance(label, Mobject): self.label = label
        elif font == "mono": self.label = mono(str(label), size, text_color)
        else: self.label = en(str(label), size + 6, text_color, italic=False)
        self.label.move_to(self.rect)
        self.shadow = shadow(self.rect, 0.03, -0.05)
        self.add(self.shadow, self.halo, self.rect, self.label)
        self.base_color = color

    def recolor(self, color):
        return AnimationGroup(self.rect.animate.set_stroke(color), *[h.animate.set_stroke(color) for h in self.halo])

def slot(w=1.5, h=0.62):
    return DashedVMobject(RoundedRectangle(width=w, height=h, corner_radius=0.12,
                                           stroke_color=FAINT, stroke_width=1.6), num_dashes=40)

class TopMarker(VGroup):
    """Gold glowing 'top' pointer: label + arrow pointing right at a slot."""
    def __init__(self, text="top", with_value=False, size=26):
        super().__init__()
        self.tri = Triangle(fill_color=GOLD, fill_opacity=1, stroke_width=0).scale(0.11).rotate(-PI / 2)
        self.line = Line(LEFT * 0.55, ORIGIN, stroke_color=GOLD, stroke_width=2.4)
        self.tri.move_to(self.line.get_end() + RIGHT * 0.06)
        self.dot = Dot(self.line.get_start(), radius=0.05, color=GOLD)
        self.halo = Dot(self.line.get_start(), radius=0.14, color=GOLD).set_opacity(0.18)
        self.lab = en(text, size, GOLD)
        self.lab.next_to(self.dot, LEFT, buff=0.14)
        self.add(self.halo, self.line, self.tri, self.dot, self.lab)

    def tip(self): return self.tri.get_right()


def pulse(mob, color=GOLD, scale=1.35, run_time=0.8):
    """Soft expanding ring that fades out (removed when done)."""
    ring = RoundedRectangle(width=mob.width + 0.08, height=mob.height + 0.08, corner_radius=0.14,
                            stroke_color=color, stroke_width=3, fill_opacity=0).move_to(mob)
    target = ring.copy().scale(scale).set_stroke(opacity=0)
    return Transform(ring, target, run_time=run_time, rate_func=rate_functions.ease_out_cubic, remover=True)


# ---------------- chapter label / title card ----------------
class ChapterLabel(VGroup):
    def __init__(self, num, zh_name, en_name):
        super().__init__()
        n = mono(f"{num:02d}", 17, GOLD)
        e = spaced(en_name.upper(), 19, INK, spacing=2.6)
        z = zh(zh_name, 17, DIM)
        row = VGroup(n, e, z).arrange(RIGHT, buff=0.26, aligned_edge=DOWN)
        z.shift(DOWN * 0.01)
        ln = Line(LEFT, RIGHT, stroke_width=1, stroke_color=FAINT)
        ln.set_width(row.width + 0.6).next_to(row, DOWN, buff=0.12).align_to(row, LEFT).shift(LEFT * 0.1)
        self.add(row, ln)
        self.line = ln
        self.to_corner(UL, buff=0.45).shift(RIGHT * 0.2 + DOWN * 0.05)


def light_line(width=9, color=CYAN, opacity=0.55):
    core = Line(LEFT * width / 2, RIGHT * width / 2, stroke_color=color, stroke_width=1.2, stroke_opacity=opacity)
    soft = Line(LEFT * width / 2, RIGHT * width / 2, stroke_color=color, stroke_width=7, stroke_opacity=0.07)
    return VGroup(soft, core)

def orb(r=0.08, color=GOLD):
    return VGroup(*[Dot(radius=r * k, color=color).set_opacity(o) for k, o in ((4.5, 0.05), (2.8, 0.12), (1.7, 0.3), (1, 1))],
                  Dot(radius=r * 0.55, color=HOT if THEME.name == "light" else WHITE))


# ---------------- motion helpers (v2) ----------------
FW = config.frame_width            # 14.22
FH = config.frame_height           # 8.0

def burst(point, color=GOLD, n=14, radius=0.65, run_time=0.6, seed=None, size=(0.016, 0.034)):
    """Small, tasteful particle burst: sparks fly out from `point` and fade (removed after)."""
    rng = np.random.default_rng(seed)
    point = np.array(point, dtype=float)
    dots = VGroup()
    vecs = []
    for k in range(n):
        a = rng.uniform(0, TAU); r = radius * rng.uniform(0.45, 1.0)
        v = np.array([math.cos(a) * r, math.sin(a) * r * 0.75, 0])
        if point.shape == (3,) and abs(point[2]) > 1e-6: v = np.array([v[0], 0, v[1]])  # 3D: burst in xz-plane
        vecs.append(v)
        dots.add(Dot(point, radius=rng.uniform(*size), color=color if k % 3 else HOT))
    ring = Circle(radius=0.05, stroke_color=color, stroke_width=2.4).move_to(point)
    ring0 = ring.copy()
    grp = VGroup(dots, ring)
    def upd(m, a):
        e = rate_functions.ease_out_cubic(a)
        for d, v in zip(dots, vecs):
            d.move_to(point + v * e); d.set_opacity((1 - a) ** 1.6)
        ring.become(ring0.copy().scale(1 + 9 * e)).set_stroke(opacity=0.8 * (1 - a) ** 2)
    return UpdateFromAlphaFunc(grp, upd, run_time=run_time, remover=True)

def _is_text(m):
    return any(isinstance(x, (Text, MarkupText)) for x in m.get_family())

def sweep(mob, color=GOLD, width=4.0, run_time=0.8, time_width=0.35):
    """Glow sweep: a bright highlight runs once along the outline of `mob` (VMobject).
    For text, a light runs along an underline instead (stroking glyph outlines looks garbled)."""
    if _is_text(mob):
        y = mob.get_bottom()[1] - 0.09
        ln = Line([mob.get_left()[0], y, 0], [mob.get_right()[0], y, 0], stroke_color=color, stroke_width=max(2.5, width * 0.8))
        return ShowPassingFlash(ln, time_width=0.5, run_time=run_time)
    c = mob.copy().set_fill(opacity=0).set_stroke(color, width=width, opacity=1)
    return ShowPassingFlash(c, time_width=time_width, run_time=run_time)

def glow_in(mob, color=GOLD, shift=UP * 0.15, run_time=0.7, outline=None):
    """Enter with a fade + a light sweep along `outline` (defaults to the mobject itself)."""
    o = outline if outline is not None else mob
    return AnimationGroup(FadeIn(mob, shift=shift, run_time=run_time),
                          sweep(o, color, run_time=run_time * 1.3))

def streak(width=FW, y=0.0, color=GOLD, length=4.5):
    """Horizontal light streak (soft halo + hot core) for chapter transitions."""
    core = Line(LEFT * length / 2, RIGHT * length / 2, stroke_color=HOT, stroke_width=2.2)
    mid = Line(LEFT * length / 2, RIGHT * length / 2, stroke_color=color, stroke_width=6, stroke_opacity=0.45)
    soft = Line(LEFT * length / 2, RIGHT * length / 2, stroke_color=color, stroke_width=26, stroke_opacity=0.10)
    g = VGroup(soft, mid, core).move_to([0, y, 0])
    return g

def sample_points(mobs, n=60, seed=0):
    rng = np.random.default_rng(seed)
    pts = [m.points for mob in mobs for m in mob.family_members_with_points() if len(m.points)]
    if not pts: return np.zeros((0, 3))
    P = np.concatenate(pts)
    return P[rng.integers(0, len(P), min(n, len(P) * 4))]

def dissolve_particles(mobs, direction=RIGHT, n=70, color=SOFT, run_time=1.0, seed=0):
    """Particle-dissolve: sparks sampled from the outlines drift away and fade."""
    rng = np.random.default_rng(seed)
    P = sample_points(mobs, n, seed)
    if not len(P): return Wait(run_time)
    dots = VGroup(*[Dot(p, radius=rng.uniform(0.012, 0.03), color=[color, GOLD, CYAN][k % 3]) for k, p in enumerate(P)])
    vel = [np.array(direction) * rng.uniform(0.8, 2.2) + np.array([rng.normal(0, 0.35), rng.normal(0, 0.35), 0]) for _ in P]
    def upd(m, a):
        e = rate_functions.ease_out_quad(a)
        for d, p, v in zip(dots, P, vel):
            d.move_to(p + v * e); d.set_opacity(max(0, math.sin(min(1, a * 1.3) * PI)) * 0.9)
    return UpdateFromAlphaFunc(dots, upd, run_time=run_time, remover=True)


def make_dust_layer(n, p, seed, spread=(11.5, 7.2), color_choices=None, rmin=0.010, rmax=0.022,
                    omin=None, omax=None, z=None):
    color_choices = color_choices or THEME.dust_colors
    omin = THEME.dust_op[0] if omin is None else omin
    omax = THEME.dust_op[1] if omax is None else omax
    rng = np.random.default_rng(seed)
    g = VGroup()
    for k in range(n):
        x, y = rng.uniform(-spread[0], spread[0]), rng.uniform(-spread[1], spread[1])
        zz = 0 if z is None else rng.uniform(*z)
        c = color_choices[0] if rng.random() < 0.7 else color_choices[1 + (k % (len(color_choices) - 1))]
        d = Dot([x, y, zz], radius=rng.uniform(rmin, rmax) * (0.6 + 0.6 * p), color=c)
        d.set_opacity(rng.uniform(omin, omax) * (0.55 + 0.45 * p))
        g.add(d)
    return g


# ---------------- base scene (v2) ----------------
class DSABase:
    """Shared by 2D (DSAScene) and 3D (DSA3DScene) scenes.
    Records captions / VO cues / SFX cues to build/timeline/<Scene>.json (consumed by lib/post.py).
    Episode code sets DSABase.BEATS (id -> (zh caption, English VO)) and DSABase.VO (id -> seconds)."""
    TIMELINE_DIR = os.environ.get("DSA_TIMELINE_DIR", "build/timeline")
    BEATS = {}
    VO = {}
    VO_DELAY = 0.15        # VO starts this long after the caption appears
    VO_TAIL = 0.6          # breathing room after a VO line

    @classmethod
    def load_episode(cls, ep_dir):
        import importlib.util
        spec = importlib.util.spec_from_file_location("ep_script", os.path.join(ep_dir, "script.py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        cls.BEATS = m.BEATS
        p = os.path.join(ep_dir, "build", "vo", "durations.json")
        cls.VO = {k: v["dur"] for k, v in json.load(open(p)).items()} if os.path.exists(p) else {}

    def setup(self):
        super().setup()
        self.events = []
        self._cap_open = None
        self.persist = []          # mobjects never cleared (camera frame, dust, rig helpers)

    @property
    def now(self): return self.renderer.time

    def sfx(self, name, gain=0.0, at=0.0):
        self.events.append({"type": "sfx", "t": round(self.now + at, 3), "name": name, "gain": gain})

    def cap_start(self, zh_text, en_text="", bid=None):
        self.cap_end()
        self._cap_open = {"type": "cap", "t": round(self.now, 3), "zh": zh_text, "en": en_text}
        if bid: self._cap_open["id"] = bid

    def cap_end(self):
        if self._cap_open:
            self._cap_open["end"] = round(self.now, 3)
            self.events.append(self._cap_open)
            self._cap_open = None

    @contextlib.contextmanager
    def beat(self, bid, extra=0.0, keep=False, hold=None):
        """One narration beat: Chinese caption + English VO cue start together; the body's animations
        run meanwhile; afterwards hold until max(VO length + tail, caption reading time)."""
        zh_text, vo_text = self.BEATS[bid]
        self.cap_start(zh_text, vo_text, bid)
        t0 = self.now
        vd = self.VO.get(bid, 0.0)
        if vd: self.events.append({"type": "vo", "t": round(t0 + self.VO_DELAY, 3), "id": bid, "dur": vd})
        yield
        need = max(vd + self.VO_DELAY + self.VO_TAIL if vd else 0, read_time(zh_text, extra), hold or 0) - (self.now - t0)
        if need > 0.02: self.wait(need)
        if not keep: self.cap_end()

    def remaining(self, bid, t0):
        """Seconds left in beat `bid` started at t0 (for spreading animations across the VO)."""
        zh_text, _ = self.BEATS[bid]
        vd = self.VO.get(bid, 0.0)
        return max(vd + self.VO_DELAY + self.VO_TAIL, read_time(zh_text)) - (self.now - t0)

    def think(self, seconds=2.0, pos=UP * 2.55 + RIGHT * 4.9):
        """'Pause & think' beat with a countdown ring (English on screen, Chinese caption)."""
        self.cap_start("暂停想一想", "Pause and think.")
        ring_bg = Circle(radius=0.34, stroke_color=FAINT, stroke_width=3)
        ring = Arc(radius=0.34, start_angle=PI / 2, angle=-TAU, stroke_color=GOLD, stroke_width=3)
        lab = spaced("PAUSE & THINK", 12, GOLD, 2.6).next_to(ring_bg, DOWN, buff=0.16)
        g = VGroup(ring_bg, ring, lab).move_to(pos)
        self.fix(g)
        self.play(FadeIn(ring_bg, scale=0.8), FadeIn(lab), run_time=0.3)
        self.sfx("tick", -4)
        self.play(Create(ring), run_time=seconds, rate_func=linear)
        self.sfx("chime", -3)
        self.play(FadeOut(g, scale=1.1), burst(ring_bg.get_center(), GOLD, 12, 0.5, 0.4), run_time=0.35)
        self.unfix(g)
        self.cap_end()

    def answer_tag(self, pos=UP * 2.55 + RIGHT * 4.9):
        t = spaced("ANSWER", 15, GOLD, 3.0)
        box = SurroundingRectangle(t, buff=0.14, corner_radius=0.08, stroke_color=GOLD, stroke_width=1.2)
        return VGroup(box, t).move_to(pos)

    def fix(self, *mobs): pass       # keep on screen regardless of camera (overridden)
    def screen(self, p): return np.array(p, dtype=float)
    def unfix(self, *mobs): pass

    def chapter(self, num, zh_name, en_name):
        """Chapter label (top-left, English first). Drawn by post.py as an ASS overlay so it stays
        pinned to the screen while the camera moves; ends at the scene's outro or chapter_end()."""
        self.chapter_end()
        self._chap = {"type": "chapter", "t": round(self.now, 3), "num": num, "en": en_name, "zh": zh_name}
        self.sfx("whoosh", -12)

    def chapter_end(self):
        if getattr(self, "_chap", None):
            self._chap["end"] = round(self.now, 3)
            self.events.append(self._chap)
            self._chap = None

    def content(self, keep=()):
        return [m for m in self.mobjects if m not in keep and m not in self.persist]

    def clear_all(self, run_time=0.6, keep=()):
        mobs = self.content(keep)
        if mobs:
            self.sfx("whoosh", -8)
            self.play(*[FadeOut(m) for m in mobs], dissolve_particles(mobs, UP, 40, run_time=run_time), run_time=run_time)

    def outro(self, run_time=1.1, y=0.2):
        """Chapter transition: a light streak sweeps across while content dissolves into particles."""
        self.chapter_end()
        mobs = self.content()
        st = streak(y=y)
        st.move_to([-FW / 2 - 3, y, 0])
        self.fix(st)
        self.sfx("whoosh", -3)
        anims = [st.animate(rate_func=rate_functions.ease_in_out_sine).move_to(self.screen([FW / 2 + 3, y, 0]))]
        if mobs:
            anims += [FadeOut(m, shift=RIGHT * 0.4) for m in mobs]
            anims.append(dissolve_particles(mobs, RIGHT, 90, run_time=run_time))
        self.play(*anims, run_time=run_time)
        self.remove(st)
        self.wait(0.1)

    def tear_down(self):
        self.cap_end()
        self.chapter_end()
        os.makedirs(self.TIMELINE_DIR, exist_ok=True)
        with open(os.path.join(self.TIMELINE_DIR, f"{type(self).__name__}.json"), "w") as f:
            json.dump({"scene": type(self).__name__, "duration": self.now, "theme": THEME.name,
                       "events": sorted(self.events, key=lambda e: e["t"])}, f, ensure_ascii=False, indent=1)
        super().tear_down()


class DSAScene(DSABase, MovingCameraScene):
    """2D scene with a time-based camera rig (non-blocking moves + gentle drift),
    HUD elements pinned to the screen, and a parallax star-dust field."""
    DRIFT = (0.07, 0.045, 0.006)       # x, y amplitude (units) and zoom breathing

    def setup(self):
        super().setup()
        self.rig = dict(x=0.0, y=0.0, w=FW)
        self.mv = None                 # current camera move
        self.t_acc = 0.0
        fr = self.camera.frame
        def upd(m, dt):
            self.t_acc += dt
            t = self.t_acc
            if self.mv:
                a = min(1.0, (t - self.mv["t0"]) / self.mv["dur"])
                e = self.mv["ease"](a)
                for k in ("x", "y", "w"):
                    self.rig[k] = self.mv["from"][k] + (self.mv["to"][k] - self.mv["from"][k]) * e
                if a >= 1: self.mv = None
            dx = self.DRIFT[0] * math.sin(t * TAU / 17.0)
            dy = self.DRIFT[1] * math.sin(t * TAU / 23.0 + 1.0)
            dz = 1 + self.DRIFT[2] * math.sin(t * TAU / 29.0)
            m.set_width(self.rig["w"] * dz)
            m.move_to([self.rig["x"] + dx, self.rig["y"] + dy, 0])
        fr.add_updater(upd)
        self.add(fr)
        self.persist.append(fr)
        self.add_dust()

    def cam(self, x=None, y=None, w=None, dur=2.0, ease=rate_functions.ease_in_out_sine, safe=True):
        """Start a non-blocking camera move (x, y = frame centre; w = frame width)."""
        to = dict(self.rig)
        if x is not None: to["x"] = x
        if y is not None: to["y"] = y
        if w is not None: to["w"] = w
        if safe: to = self.safe_target(to)
        self.mv = dict(t0=self.t_acc, dur=max(dur, 1e-3), ease=ease, **{"from": dict(self.rig), "to": to})

    # safe area in px @1080p: sides 80, top 80 (125 while the chapter HUD is shown), bottom 230 (caption band)
    SAFE_PX = (80, 80, 125, 230)

    def safe_target(self, to):
        """Adjust a camera target so every content mobject that would be visible sits fully inside the
        safe area (no panel cropped at a frame edge). Things entirely outside the target frame stay out."""
        for _ in range(4):                             # iterate: widening can bring more mobjects into view
            new = self._safe_once(to)
            if all(abs(new[k] - to[k]) < 1e-3 for k in ("x", "y", "w")): break
            to = new
        return to

    def _safe_once(self, to):
        x, y, w = to["x"], to["y"], to["w"]
        side, top0, top_hud, bot = self.SAFE_PX
        top = top_hud if getattr(self, "_chap", None) else top0
        fs, ft, fb = side / 1920, top / 1080, bot / 1080
        slack = 0.12                                   # drift + zoom breathing
        boxes = []
        for m in self.content():
            if m.width < 0.05 and m.height < 0.05: continue
            if isinstance(m, VMobject) and not m.submobjects and m.get_fill_opacity() == 0 and m.get_stroke_opacity() == 0: continue
            (x0, y0, _), (x1, y1, _) = m.get_corner(DL), m.get_corner(UR)
            h = w * 9 / 16
            if x1 < x - w / 2 or x0 > x + w / 2 or y1 < y - h / 2 or y0 > y + h / 2: continue
            boxes.append((x0 - slack, y0 - slack, x1 + slack, y1 + slack))
        if not boxes: return to
        bx0 = min(b[0] for b in boxes); by0 = min(b[1] for b in boxes)
        bx1 = max(b[2] for b in boxes); by1 = max(b[3] for b in boxes)
        need_w = max(w, (bx1 - bx0) / (1 - 2 * fs), (by1 - by0) / (1 - ft - fb) * 16 / 9)
        w = min(need_w, FW * 1.08)
        h = w * 9 / 16
        lo, hi = bx1 - w / 2 + w * fs, bx0 + w / 2 - w * fs
        x = min(max(x, lo), hi) if lo <= hi else (lo + hi) / 2
        lo, hi = by1 - h / 2 + h * ft, by0 + h / 2 - h * fb
        y = min(max(y, lo), hi) if lo <= hi else (lo + hi) / 2
        return dict(x=x, y=y, w=w)

    def focus(self, mob, margin=0.6, dur=2.0, max_w=FW, min_w=7.0, caption_band=True):
        """Frame `mob` with margin, keeping it above the caption band."""
        # usable band of the frame: below the chapter label (top 10%) and above the caption band (bottom 23%)
        use = 0.67 if caption_band else 1.0
        w = max(min_w, min(max_w, max((mob.width + 2 * margin) * 1.04, (mob.height + 2 * margin) / use * 16 / 9)))
        h = w * 9 / 16
        c = mob.get_center()
        y = c[1] - (0.065 * h if caption_band else 0)
        self.cam(c[0], y, w, dur)

    def fix(self, *mobs):
        """Map mobjects given in default-frame (screen) coordinates to the current camera frame."""
        fr = self.camera.frame; k = fr.width / FW; c = fr.get_center()
        for m in mobs: m.scale(k, about_point=ORIGIN).shift(c)

    def screen(self, p):
        fr = self.camera.frame
        return fr.get_center() + np.array(p, dtype=float) * fr.width / FW

    def add_dust(self):
        """Three parallax layers of star dust (far layers move/zoom less than the content plane)."""
        self.dust = []
        for p, n, seed in ((0.18, 70, 11), (0.45, 45, 12), (0.8, 22, 13)):
            g = make_dust_layer(n, p, seed)
            g.z_index = -5
            st = {"k": 1.0, "c": np.zeros(3), "v": np.array([0.05, 0.012, 0]) * (0.4 + p), "p": p}
            def upd(m, dt, st=st):
                fr = self.camera.frame
                fc = fr.get_center(); fw = fr.width
                k = (fw / FW) ** (1 - st["p"])
                c = k * (st["v"] * self.t_acc - fc * st["p"]) + fc
                m.shift(-st["c"]).scale(k / st["k"], about_point=ORIGIN).shift(c)
                st["k"], st["c"] = k, c
            g.add_updater(upd)
            self.add(g); self.persist.append(g); self.dust.append(g)

    def chapter(self, num, zh_name, en_name):
        # every chapter opens with a slow push-in
        self.rig["w"] = FW * 1.06
        self.cam(w=FW, dur=3.0, ease=rate_functions.ease_out_sine)
        super().chapter(num, zh_name, en_name)

    def content(self, keep=()):
        return [m for m in self.mobjects if m not in keep and m not in self.persist]


class DSA3DScene(DSABase, ThreeDScene):
    """3D scene: slow orbiting camera (theta oscillates), 3D star dust (true parallax),
    HUD text fixed in frame."""
    ORBIT = (-90, 20, 34.0)     # centre theta (deg), amplitude (deg), period (s)
    PHI = 70

    def setup(self):
        super().setup()
        self.t_acc = 0.0
        self.set_camera_orientation(phi=self.PHI * DEGREES, theta=self.ORBIT[0] * DEGREES)
        rig = Mobject()
        def upd(m, dt):
            self.t_acc += dt
            th = self.ORBIT[0] + self.ORBIT[1] * math.sin(self.t_acc * TAU / self.ORBIT[2])
            self.renderer.camera.theta_tracker.set_value(th * DEGREES)
        rig.add_updater(upd)
        self.add(rig); self.persist.append(rig)
        d = VGroup(make_dust_layer(80, 0.6, 21, spread=(10, 6), z=(-6, 6)),
                   make_dust_layer(40, 0.9, 22, spread=(8, 5), z=(-3, 3)))
        self.add(d); self.persist.append(d)

    def fix(self, *mobs):
        self.add_fixed_in_frame_mobjects(*mobs)

    def unfix(self, *mobs):
        pass


# ---------------- reusable stack visual ----------------
class StackView:
    """Vertical stack/array visual bound to a scene.
    bottom: point at the centre of the base line. Slot i centre = bottom + UP*(pad + i*(h+gap) + h/2).
    Index -1 is a virtual slot just below the base (used by the top=-1 marker)."""
    def __init__(self, scene, capacity, bottom=ORIGIN, w=1.5, h=0.58, gap=0.1, pad=0.12,
                 bucket=True, index_labels=False, index_fmt="{i}", font_size=26, marker=True,
                 marker_value=False, slot_dashes=True):
        self.s, self.cap, self.w, self.h, self.gap, self.pad = scene, capacity, w, h, gap, pad
        self.bottom = np.array(bottom, dtype=float)
        self.font_size = font_size
        self.cells = []
        self.top_index = -1
        self.trails = []
        self.group = VGroup()
        H = pad + capacity * (h + gap) + 0.15
        if bucket:
            L = self.bottom + LEFT * (w / 2 + 0.16); R = self.bottom + RIGHT * (w / 2 + 0.16)
            self.bucket = VMobject(stroke_color=CYAN, stroke_width=2.2).set_points_as_corners(
                [L + UP * H, L, R, R + UP * H])
            self.bucket_halo = glow_stroke(self.bucket, CYAN, widths=(12, 6), opacities=(0.05, 0.12))
            self.group.add(self.bucket_halo, self.bucket)
        else:
            self.bucket = None
        self.slots = VGroup(*[slot(w, h).move_to(self.pos(i)) for i in range(capacity)]) if slot_dashes else VGroup()
        self.group.add(self.slots)
        self.idx = VGroup()
        if index_labels:
            for i in range(capacity):
                t = mono(index_fmt.format(i=i), 16, DIM).next_to(self.pos(i) + RIGHT * w / 2, RIGHT, buff=0.32)
                self.idx.add(t)
            self.group.add(self.idx)
        self.marker = None
        if marker:
            self.marker = TopMarker(with_value=marker_value)
            self._place_marker(self.marker, -1)
            if marker_value:
                self.mval = mono("= -1", 17, GOLD).next_to(self.marker.lab, DOWN, buff=0.06)

    def build(self, run_time=0.9):
        """Entrance: bucket drawn with a light sweep, slots cascade in."""
        anims = []
        if self.bucket is not None:
            anims += [Create(self.bucket), FadeIn(self.bucket_halo), sweep(self.bucket, GOLD, 5, run_time * 1.4)]
        anims.append(LaggedStart(*[FadeIn(s, shift=UP * 0.1) for s in self.slots], lag_ratio=0.15))
        if len(self.idx): anims.append(FadeIn(self.idx))
        return AnimationGroup(*anims, run_time=run_time)

    def pos(self, i):
        return self.bottom + UP * (self.pad + i * (self.h + self.gap) + self.h / 2)

    def _place_marker(self, m, i):
        tip = self.pos(i) + LEFT * (self.w / 2 + 0.06)
        if i < 0: tip = self.bottom + LEFT * (self.w / 2 + 0.24) + DOWN * 0.18
        m.shift(tip - m.tip())

    def _marker_delta(self, i):
        probe = self.marker.copy(); self._place_marker(probe, i)
        return probe.tip() - self.marker.tip()

    def marker_to(self, i, run_time=0.5):
        d = self._marker_delta(i)
        anims = [self.marker.animate(run_time=run_time).shift(d)]
        if hasattr(self, "mval"):
            new = mono(f"= {i}", 17, GOLD).move_to(self.mval.get_left() + d, aligned_edge=LEFT)
            anims.append(Transform(self.mval, new, run_time=run_time))
        return anims

    def set_value_label(self, i): return []

    def make_cell(self, label, color=CYAN, **kw):
        return Cell(label, self.w, self.h, color=color, size=self.font_size, **kw)

    def _trail(self, mob, color=GOLD, width=4):
        tr = TracedPath(mob.get_center, stroke_color=color, stroke_width=width, dissipating_time=0.4, stroke_opacity=0.9)
        self.s.add(tr); self.trails.append(tr)
        return tr

    def push(self, label, run_time=0.75, color=CYAN, from_point=None, from_mob=None, sfx=True, extra=(),
             spark=True, path_arc=0.0):
        """Animate a push: the new cell flies in on a light trail (optionally out of a code token
        `from_mob`), the top marker follows, and a small spark burst marks the landing."""
        i = len(self.cells)
        c = self.make_cell(label, color)
        c.move_to(self.pos(i)); c.save_state()
        anims = []
        if from_mob is not None:
            start = from_mob.get_center()
            c.move_to(start).scale(0.35).fade(1)
            ghost = from_mob.copy().set_color(GOLD)
            anims.append(ghost.animate(rate_func=rate_functions.ease_in_out_cubic, path_arc=path_arc)
                         .move_to(self.pos(i)).fade(1))
            anims.append(Indicate(from_mob, color=GOLD, scale_factor=1.15, run_time=run_time * 0.6))
            self.s.add(ghost)
        else:
            start = from_point if from_point is not None else self.pos(self.cap - 1) + UP * 1.25
            c.move_to(start).fade(1)
        self.s.add(c)
        self._trail(c)
        anims.append(Restore(c, rate_func=rate_functions.ease_out_cubic, path_arc=path_arc))
        if self.marker is not None:
            anims += self.marker_to(i) + self.set_value_label(i)
        if sfx: self.s.sfx("push", 0, at=run_time * 0.8)
        land = []
        if spark:
            land = [Succession(Wait(run_time * 0.8), AnimationGroup(burst(self.pos(i), GOLD, 12, 0.55, 0.5),
                                                                    pulse(c.rect, GOLD, 1.22, 0.45)))]
        self.s.play(*anims, *land, *extra, run_time=run_time + (0.4 if spark else 0))
        if from_mob is not None: self.s.remove(ghost)
        self.cells.append(c)
        self.top_index = i
        return c

    def pop(self, run_time=0.7, to_point=None, fade=True, sfx=True, extra=(), spark=True):
        c = self.cells.pop()
        i = len(self.cells) - 1
        self._trail(c)
        tgt = to_point if to_point is not None else self.pos(self.cap - 1) + UP * 1.3
        anims = [c.animate(rate_func=rate_functions.ease_in_out_cubic).move_to(tgt).fade(1 if fade else 0)]
        if self.marker is not None: anims += self.marker_to(i) + self.set_value_label(i)
        if sfx: self.s.sfx("pop", 0, at=0.05)
        if spark: anims.append(burst(c.get_center(), CYAN, 10, 0.5, run_time * 0.8))
        self.s.play(*anims, *extra, run_time=run_time)
        if fade: self.s.remove(c)
        self.top_index = i
        return c

    def reject(self, label, run_time=0.8, from_mob=None):
        """push on a full stack: element approaches, crimson flash + sparks, wiggles."""
        c = self.make_cell(label, CRIMSON)
        c.move_to(self.pos(self.cap - 1) + UP * (self.h + 0.12)); c.save_state()
        if from_mob is not None: c.move_to(from_mob.get_center()).scale(0.35).fade(1)
        else: c.move_to(self.pos(self.cap - 1) + UP * 1.45).fade(1)
        self.s.add(c); self._trail(c, CRIMSON, 3)
        flash = self.bucket.copy().set_stroke(CRIMSON, width=4) if self.bucket else None
        self.s.play(Restore(c), run_time=run_time * 0.6, rate_func=rate_functions.ease_in_quad)
        self.s.sfx("error", 0)
        anims = [Wiggle(c, scale_value=1.05, rotation_angle=0.05 * TAU, run_time=0.5),
                 burst(c.get_bottom(), CRIMSON, 12, 0.5, 0.5)]
        if flash: anims.append(ShowPassingFlash(flash, time_width=1.0, run_time=0.6))
        self.s.play(*anims)
        return c

    def clear_trails(self):
        for t in self.trails: self.s.remove(t)
        self.trails = []

    def all(self):
        g = VGroup(self.group)
        if self.marker is not None: g.add(self.marker)
        if hasattr(self, "mval"): g.add(self.mval)
        return g


def result_tag(text, color=GOLD, size=22, prefix="→ "):
    t = mono(prefix + text, size, color)
    box = SurroundingRectangle(t, buff=0.12, corner_radius=0.08, stroke_color=color, stroke_width=1.4,
                               fill_color=PANEL, fill_opacity=0.92)
    return VGroup(box, t, shadow(box, 0.03, -0.05))


# ---------------- 3D wireframe elements ----------------
def wire_box(w, d, h, color=CYAN, width=1.8, fill=0.10, fill_color=None):
    fill_color = fill_color or THEME.cell_fill
    """Glowing wireframe slab (a Prism with translucent faces) centred at origin: x=w, y=d, z=h."""
    p = Prism(dimensions=[w, d, h], fill_color=fill_color, fill_opacity=fill, stroke_color=color, stroke_width=width)
    return p

def face_label(text, w, d, size=40, color=INK, font="mono"):
    """Label lying on the front (-y) face of a slab."""
    t = mono(text, size, color) if font == "mono" else en(text, size, color, italic=False)
    t.rotate(PI / 2, axis=RIGHT)
    t.move_to([0, -d / 2 - 0.01, 0])
    return t

def wire_bucket(w, d, H, color=CYAN, width=2.4):
    """Open-top 3D bucket: bottom rectangle + four vertical edges (+ faint halo)."""
    x, y = w / 2, d / 2
    bot = [[-x, -y, 0], [x, -y, 0], [x, y, 0], [-x, y, 0]]
    edges = VGroup()
    for k in range(4):
        edges.add(Line(bot[k], bot[(k + 1) % 4], stroke_color=color, stroke_width=width))
        edges.add(Line(bot[k], [bot[k][0], bot[k][1], H], stroke_color=color, stroke_width=width))
    halo = VGroup(*[e.copy().set_stroke(color, width=10, opacity=0.10) for e in edges])
    return VGroup(halo, edges)


# ---------------------------------------------------------------- shared end card (every episode)
BRAND = CVS.CONFIG.get("brand", {})   # config.json -> brand.* (default: Kuaizengji logo + www.kuaizengji.com)
MUSIC_CREDIT = ("Original score composed for this series.",
                "Piano samples: \u201cSalamander Grand Piano\u201d by Alexander Holm, CC BY 3.0 (SF2 version by FreePats.org).",
                "Other sounds synthesised in code.")


def brand_logo(height=0.9):
    """Brand logo from config.json (brand.logo_light / brand.logo_dark; default = Kuaizengji 快增绩), loaded as-is.
    The *_light variant (dark ink) is for light backgrounds; the dark theme uses *_dark. Returns None if disabled."""
    if not BRAND.get("enabled", True): return None
    p = CVS.asset(BRAND.get("logo_dark" if THEME.name == "dark" else "logo_light", ""))
    if not p or not os.path.exists(p): return None
    logo = SVGMobject(p)
    logo.set_stroke(width=0)
    return logo.scale_to_fit_height(height)


def end_card_parts(title, next_en, credit=MUSIC_CREDIT):
    """Layout of the end card (centred): title / light line / NEXT · ... / logo / Powered by / small credit.
    Everything sits inside the safe area, above the caption band."""
    title_m = spaced(title.upper(), 46, INK, 1.8).move_to(UP * 2.25)
    line = light_line(8, CYAN, 0.5).move_to(UP * 1.6)
    o = orb(0.07, GOLD).move_to(line.get_left())
    nxt = spaced(f"NEXT  ·  {next_en.upper()}", 15, GOLD, 3.0).move_to(UP * 1.15)
    logo = brand_logo(0.92)
    logo = logo.move_to(DOWN * 0.05) if logo is not None else VGroup(Dot(radius=0.001, fill_opacity=0)).move_to(DOWN * 0.05)
    # soft glow: many faint concentric ellipses (no hard edge)
    halo = VGroup(*[Ellipse(width=logo.width * (0.5 + 0.09 * k), height=logo.height * (0.9 + 0.13 * k), stroke_width=0,
                            fill_color=CYAN, fill_opacity=0.0) for k in range(12)]).move_to(logo)
    pb = CVS.powered_by_text()
    powered = (en(pb, 26, SOFT, italic=False) if pb else VGroup(Dot(radius=0.001, fill_opacity=0))).next_to(logo, DOWN, buff=0.32)
    cred = VGroup(*[en(t, 19 if i == 0 else 17, DIM) for i, t in enumerate(credit)]).arrange(DOWN, buff=0.07)
    cred.next_to(powered, DOWN, buff=0.3)
    return dict(title=title_m, line=line, orb=o, next=nxt, logo=logo, halo=halo, powered=powered, credit=cred)


def end_card_in(P):
    """Gentle entrance for the end-card parts (after the line + orb are already in place)."""
    halo_in = AnimationGroup(*[e.animate.set_fill(opacity=0.011) for e in P["halo"]])
    return [FadeIn(P["title"], shift=UP * 0.1), FadeIn(P["next"]),
            Flash(P["orb"], color=GOLD, line_length=0.25, num_lines=12, flash_radius=0.3),
            Succession(Wait(0.35), AnimationGroup(FadeIn(P["logo"], scale=0.96), halo_in, run_time=1.0)),
            Succession(Wait(0.8), FadeIn(P["powered"], shift=UP * 0.08, run_time=0.6)),
            Succession(Wait(1.0), FadeIn(P["credit"], run_time=0.6))]


def _end_card(self, title, next_en, beat_id=None, hold=5.6, credit=MUSIC_CREDIT):
    """Shared end card: content dissolves under a light streak, then title / next / logo / credits."""
    P = end_card_parts(title, next_en, credit)
    line, o = P["line"], P["orb"]
    mobs = self.content()
    st = streak(y=line.get_center()[1]); st.move_to([-FW / 2 - 3, line.get_center()[1], 0]); self.fix(st)
    self.sfx("whoosh", -3)
    self.add(o, P["halo"])
    self.play(*[FadeOut(m, shift=RIGHT * 0.4) for m in mobs], dissolve_particles(mobs, RIGHT, 80, run_time=1.0),
              st.animate.move_to(self.screen([FW / 2 + 3, line.get_center()[1], 0])), Create(line[1]), FadeIn(line[0]),
              o.animate.move_to(line.get_center()), run_time=1.1)
    self.remove(st)
    self.chapter_end()
    self.sfx("chime_lo", -2)
    ctx = self.beat(beat_id, hold=hold) if beat_id else contextlib.nullcontext()
    with ctx:
        self.play(*end_card_in(P), run_time=1.6)
        if not beat_id: self.wait(hold)
    self.play(*[FadeOut(m) for m in self.content()], run_time=0.7)


DSABase.end_card = _end_card
