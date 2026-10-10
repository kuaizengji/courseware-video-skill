"""Example episode - Stacks (data structures series). Worked example for the courseware-video toolkit.
Narration beats: script.py (zh caption + English VO).
On-screen text is English; the Chinese explanation lives in the bottom caption (post.py).
Knowledge points only - no homework/lab/task content (series rule).
Render: see render.sh"""
import sys, os
EP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.environ.get("CVS_HOME") or os.path.join(EP, "..", ".."), "toolkit", "lib"))
from dsa_style import *
DSABase.load_episode(EP)


# ================================================================ 3D helpers (title / definition)
class Stack3D:
    """Wireframe 3D stack along +z: slabs drop in from above (push) and rise out (pop)."""
    def __init__(self, scene, cap, base, w=1.7, d=1.1, h=0.5, gap=0.08, labels=True):
        self.s, self.cap, self.base, self.w, self.d, self.h, self.gap = scene, cap, np.array(base, float), w, d, h, gap
        self.H = 0.12 + cap * (h + gap) + 0.15
        self.bucket = wire_bucket(w + 0.3, d + 0.3, self.H).shift(self.base)
        self.slabs = []
        self.labels = labels

    def pos(self, i): return self.base + OUT * (0.12 + i * (self.h + self.gap) + self.h / 2)

    def make(self, label, color=CYAN):
        b = wire_box(self.w, self.d, self.h, color, 1.8, 0.16)
        g = VGroup(b)
        if label is not None and self.labels:
            g.add(face_label(label, self.w, self.d, 40, INK))
        return g

    def push(self, label, run_time=0.7, color=CYAN, sfx=True):
        i = len(self.slabs)
        g = self.make(label, color).move_to(self.pos(i))
        g.save_state(); g.shift(OUT * 2.6).fade(1)
        self.s.add(g)
        if sfx: self.s.sfx("push", 0, at=run_time * 0.8)
        self.s.play(Restore(g, rate_func=rate_functions.ease_out_cubic),
                    Succession(Wait(run_time * 0.8), burst(self.pos(i) + DOWN * self.d / 2, GOLD, 12, 0.6, 0.5)),
                    run_time=run_time + 0.4)
        self.slabs.append(g)
        return g


class S00_Title(DSA3DScene):
    ORBIT = (-90, 26, 30.0)
    PHI = 72

    def construct(self):
        st = Stack3D(self, 4, base=[3.3, 0, -1.7], w=1.9, d=1.2, h=0.46, labels=False)
        line = light_line(7.2, CYAN, 0.6).move_to(LEFT * 2.3 + DOWN * 0.15)
        o = orb(0.08, GOLD).move_to(line.get_left())
        title = spaced("STACKS", 84, INK, spacing=1.7).move_to(LEFT * 2.3 + UP * 1.0)
        sub = en("Last In, First Out", 44, GOLD).move_to(LEFT * 2.3 + DOWN * 0.75)
        tiny = spaced("DATA STRUCTURES & ALGORITHMS", 13, DIM, spacing=3.2).move_to(LEFT * 2.3 + DOWN * 1.45)
        self.fix(line, o, title, sub, tiny)
        self.remove(line, o, title, sub, tiny)
        self.sfx("swell", 0)
        self.play(Create(st.bucket[1]), FadeIn(st.bucket[0]), run_time=1.2)
        for k in range(4):
            st.push(None, run_time=0.45, color=GOLD if k == 3 else CYAN, sfx=k % 2 == 0)
        with self.beat("t0", hold=4.6):
            self.play(Create(line[1]), FadeIn(line[0]), run_time=0.8)
            self.add(o)
            self.sfx("boom", 0, at=0.6)
            self.play(o.animate.move_to(line.get_center()), FadeIn(title, shift=UP * 0.15, scale=1.04), run_time=1.0,
                      rate_func=rate_functions.ease_out_cubic)
            self.play(FadeIn(sub, shift=UP * 0.12), Flash(o, color=GOLD, line_length=0.3, num_lines=14, flash_radius=0.35),
                      run_time=0.8)
            self.play(FadeIn(tiny), o.animate.shift(RIGHT * 0.6), run_time=0.8)
        self.outro()


class S01_Definition(DSA3DScene):
    ORBIT = (-90, 18, 36.0)
    PHI = 68

    def side(self, *rows, y=1.4, x=3.3):
        g = VGroup(*rows).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        if g.width > 5.9: g.scale_to_fit_width(5.9)
        g.move_to([0.5, y, 0], aligned_edge=LEFT)
        self.fix(g); self.remove(g)
        return g

    def arrow3d(self, z, text, color, x_left):
        """Pointer in the slab plane (front face), label billboarded toward the camera."""
        y = -0.6
        ln = Line([x_left - 1.0, y, z], [x_left - 0.08, y, z], stroke_color=color, stroke_width=2.6)
        tip = Dot([x_left - 0.08, y, z], radius=0.05, color=color)
        lab = en(text, 44, color).move_to([x_left - 1.75, y, z])
        self.add_fixed_orientation_mobjects(lab); self.remove(lab)
        return VGroup(ln, tip), lab

    def construct(self):
        self.chapter(1, "定义", "Definition")
        st = Stack3D(self, 6, base=[-3.1, 0, -2.45], w=2.3, d=1.3, h=0.62)
        t1 = self.side(en("A stack is a special list:", 46, INK),
                       en("insert and delete at the same end.", 40, SOFT))
        with self.beat("d1") as _:
            self.play(Create(st.bucket[1]), FadeIn(st.bucket[0]), FadeIn(t1, shift=LEFT * 0.2), run_time=0.9)
            for v in (3, 4, 8, 6):
                st.push(str(v), run_time=0.45)
        xl = st.base[0] - st.w / 2
        a_top, l_top = self.arrow3d(st.pos(3)[2], "top", GOLD, xl)
        a_bot, l_bot = self.arrow3d(st.pos(0)[2], "bottom", SOFT, xl)
        with self.beat("d2"):
            self.play(Create(a_top), FadeIn(l_top, shift=RIGHT * 0.2), sweep(st.slabs[3][0], GOLD, 4, 0.8), run_time=0.7)
            self.play(Create(a_bot), FadeIn(l_bot, shift=RIGHT * 0.2), run_time=0.7)
        t2 = self.side(en("Everything happens at the top.", 46, GOLD), y=1.4)
        t3 = self.side(en("Nothing happens at the bottom.", 46, DIM), y=0.55)
        with self.beat("d3"):
            self.play(FadeOut(t1, shift=UP * 0.2), FadeIn(t2, shift=LEFT * 0.2), run_time=0.6)
            self.sfx("chime", -4)
            self.play(st.slabs[3][0].animate.set_stroke(GOLD, width=3), sweep(st.slabs[3][0], HOT, 3, 0.7), run_time=0.7)
            self.play(FadeIn(t3, shift=LEFT * 0.2), st.slabs[0].animate.fade(0.6), run_time=0.7)
        outs = [np.array([0.3, 0, 1.0]), np.array([2.7, 0, 1.0])]
        t4 = self.side(en("6 went in last  →  6 comes out first", 40, INK), y=-1.7)
        with self.beat("d4"):
            self.play(FadeOut(t2), FadeOut(t3), st.slabs[0].animate.fade(-1.5), run_time=0.4)
            tags = []
            for k in range(2):
                g = st.slabs.pop()
                zdrop = st.h + st.gap
                self.sfx("pop", 0)
                self.play(g.animate(path_arc=-0.6).move_to(outs[k]), a_top.animate.shift(IN * zdrop),
                          l_top.animate.shift(IN * zdrop),
                          burst(st.pos(len(st.slabs)) + DOWN * st.d / 2, CYAN, 10, 0.5, 0.5), run_time=0.75)
                tg = en(["1st out", "2nd out"][k], 38, GOLD).move_to(outs[k] + OUT * 0.85 + DOWN * 0.2)
                self.add_fixed_orientation_mobjects(tg); self.remove(tg)
                self.play(FadeIn(tg), run_time=0.3)
                tags.append(tg)
            self.play(FadeIn(t4, shift=UP * 0.1), run_time=0.5)
        # LIFO card
        words = ["Last", "In,", "First", "Out"]
        row = VGroup(*[VGroup(en(w[0], 96, GOLD, italic=False), en(w[1:], 64, INK, italic=False)).arrange(RIGHT, buff=0.04, aligned_edge=DOWN)
                       for w in words]).arrange(RIGHT, buff=0.55, aligned_edge=DOWN).move_to(UP * 0.5)
        lifo = VGroup(*[en(ch, 150, GOLD, italic=False) for ch in "LIFO"]).arrange(RIGHT, buff=0.5).move_to(UP * 0.5)
        lab2 = spaced("LIFO LIST", 18, SOFT, 4.0).move_to(DOWN * 1.15)
        self.fix(row, lifo, lab2); self.remove(row, lifo, lab2)
        with self.beat("d5"):
            mobs = self.content()
            self.sfx("whoosh", -6)
            self.play(*[FadeOut(m) for m in mobs], dissolve_particles(mobs, UP, 80, run_time=0.8), run_time=0.8)
            self.play(LaggedStart(*[FadeIn(w, shift=UP * 0.15) for w in row], lag_ratio=0.25), run_time=1.1)
            self.sfx("chime_lo", 0)
            self.play(*[FadeOut(w[1]) for w in row], *[ReplacementTransform(row[i][0], lifo[i]) for i in range(4)], run_time=0.9)
            ul = Line(lifo.get_corner(DL) + DOWN * 0.15, lifo.get_corner(DR) + DOWN * 0.15, stroke_color=GOLD, stroke_width=3)
            self.fix(ul)
            self.play(FadeIn(lab2, shift=UP * 0.1), ShowPassingFlash(ul, time_width=0.5), run_time=0.9)
        self.outro()


# ================================================================ 02 operations
class S02_Operations(DSAScene):
    def card(self, sig, desc, color=GOLD, y=0.9):
        g = VGroup(mono(sig, 36, color), en(desc, 30, SOFT)).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        return g.move_to([-0.6, y, 0], aligned_edge=LEFT)

    def swap(self, old, new):
        a = [glow_in(new[0], GOLD, shift=UP * 0.15, run_time=0.5), FadeIn(new[1:], shift=UP * 0.15, run_time=0.5)]
        if old is not None: a.append(FadeOut(old, shift=UP * 0.2, run_time=0.4))
        return a

    def construct(self):
        self.chapter(2, "操作", "Operations")
        terms = VGroup(*[mono(t, 54, GOLD if i < 2 else CYAN) for i, t in enumerate(["push", "pop", "top"])]).arrange(RIGHT, buff=1.4).move_to(UP * 0.5)
        sv = StackView(self, 3, bottom=LEFT * 3.5 + DOWN * 1.95, w=1.6, h=0.62, gap=0.12, font_size=30)
        hdr = terms.copy().scale(0.5).arrange(RIGHT, buff=0.5).move_to(RIGHT * 3.7 + UP * 2.55)
        with self.beat("o1"):
            self.sfx("chime", -5)
            self.play(LaggedStart(*[glow_in(t, GOLD) for t in terms], lag_ratio=0.3), run_time=1.1)
            self.play(Transform(terms, hdr), sv.build(), run_time=0.9)
            self.play(FadeIn(sv.marker, shift=RIGHT * 0.2), run_time=0.4)
        def hl(k):
            return [terms[j].animate.set_opacity(1 if j == k else 0.35) for j in range(3)]
        self.cam(x=-0.4, y=-0.25, w=13.0, dur=4.0)
        card = self.card("push(A)", "adds an element to the top")
        with self.beat("o2"):
            self.play(*self.swap(None, card), *hl(0), run_time=0.5)
            sv.push("A", from_mob=card[0][5], path_arc=0.5)
        c2 = self.card("push(B)", "B becomes the new top")
        with self.beat("o3"):
            self.play(*self.swap(card, c2), run_time=0.5); card = c2
            sv.push("B", from_mob=card[0][5], path_arc=0.5)
        c2 = self.card("pop()", "removes the top and returns it")
        with self.beat("o4"):
            self.play(*self.swap(card, c2), *hl(1), run_time=0.5); card = c2
            r = result_tag("returns B").next_to(card, DOWN, buff=0.45, aligned_edge=LEFT)
            b = sv.pop(run_time=0.8, to_point=r.get_right() + RIGHT * 1.15, fade=False)
            self.play(FadeIn(r, shift=RIGHT * 0.15), sweep(r[0], GOLD, 3, 0.6), run_time=0.5)
        self.play(FadeOut(b, shift=RIGHT * 0.3), FadeOut(r), run_time=0.35)
        c2 = self.card("top()", "returns the top, without removing it", CYAN)
        with self.beat("o5"):
            self.play(*self.swap(card, c2), *hl(2), run_time=0.5); card = c2
            a = sv.cells[-1]
            r = result_tag("returns A", CYAN).next_to(card, DOWN, buff=0.45, aligned_edge=LEFT)
            ghost = a.copy()
            self.sfx("chime_hi", -3)
            self.play(pulse(a.rect, CYAN), ghost.animate(path_arc=-0.4).move_to(r.get_right() + RIGHT * 1.15).fade(0.35),
                      FadeIn(r), run_time=0.9)
            stays = en("A is still in the stack", 26, SOFT).next_to(sv.pos(0) + RIGHT * sv.w / 2, RIGHT, buff=0.4)
            self.play(FadeIn(stays, shift=LEFT * 0.1), sweep(a.rect, CYAN, 3, 0.6), run_time=0.5)
        sv.clear_trails()
        self.cam(x=0, y=0, w=FW, dur=1.2)
        self.clear_all(keep=(terms,))
        # ---- isEmpty / isFull / failures
        sv = StackView(self, 4, bottom=LEFT * 3.5 + DOWN * 2.2, w=1.6, h=0.56, gap=0.1, font_size=28)
        cap_lab = spaced("CAPACITY  4", 14, SOFT, 2.6).next_to(sv.pos(3), UP, buff=0.55)
        chk = VGroup(mono("isEmpty()", 36, CYAN), mono("isFull()", 36, CYAN)).arrange(DOWN, aligned_edge=LEFT, buff=0.4).move_to([0.0, 1.2, 0], aligned_edge=LEFT)
        with self.beat("o6"):
            self.play(FadeOut(terms, shift=UP * 0.2), sv.build(), FadeIn(cap_lab), run_time=0.9)
            self.play(FadeIn(sv.marker), LaggedStart(*[glow_in(c, CYAN) for c in chk], lag_ratio=0.3), run_time=0.9)
        self.cam(x=-0.5, y=-0.35, w=12.8, dur=5.0)
        r1 = result_tag("true").next_to(chk[0], RIGHT, buff=0.4)
        with self.beat("o7"):
            self.play(chk[0].animate.set_color(GOLD), run_time=0.3)
            self.sfx("chime_hi", -3)
            self.play(FadeIn(r1, shift=RIGHT * 0.1), sweep(sv.bucket, GOLD, 4, 0.7), run_time=0.6)
            self.play(FadeOut(r1), chk[0].animate.set_color(CYAN), chk[1].animate.set_color(GOLD), run_time=0.3)
            for v in "ABCD": sv.push(v, run_time=0.3, sfx=v in "AC")
            r2 = result_tag("true").next_to(chk[1], RIGHT, buff=0.4)
            self.sfx("chime_hi", -3)
            self.play(FadeIn(r2, shift=RIGHT * 0.1), run_time=0.4)
        e_card = VGroup(mono("push(E)", 32, CRIMSON), mono("→ null", 32, CRIMSON), spaced("OVERFLOW", 16, CRIMSON, 3.0)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to([0.0, -1.2, 0], aligned_edge=LEFT)
        with self.beat("o8"):
            self.play(FadeOut(r2), FadeIn(e_card[0]), run_time=0.4)
            e = sv.reject("E", from_mob=e_card[0][5])
            self.play(FadeIn(e_card[1:], shift=RIGHT * 0.1), e.animate.shift(UP * 0.6 + RIGHT * 0.8).fade(1), run_time=0.7)
            self.remove(e)
        u_card = VGroup(VGroup(mono("pop()", 32, CRIMSON), mono("top()", 32, CRIMSON)).arrange(RIGHT, buff=0.5),
                        mono("→ null", 32, CRIMSON), spaced("UNDERFLOW", 16, CRIMSON, 3.0)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to([0.0, -1.2, 0], aligned_edge=LEFT)
        with self.beat("o9"):
            self.play(FadeOut(e_card), chk[1].animate.set_color(CYAN), run_time=0.3)
            for _ in range(4): sv.pop(run_time=0.32, sfx=_ % 2 == 0)
            self.play(FadeIn(u_card[0]), run_time=0.3)
            self.sfx("error", 0)
            self.play(ShowPassingFlash(sv.bucket.copy().set_stroke(CRIMSON, width=5), time_width=1.0),
                      burst(sv.pos(0), CRIMSON, 12, 0.6, 0.6), FadeIn(u_card[1:], shift=RIGHT * 0.1), run_time=0.7)
        sv.clear_trails()
        self.outro()


# ================================================================ 03 applications
class S03_Applications(DSAScene):
    def construct(self):
        self.chapter(3, "应用", "Applications")
        def card(icon, title):
            box = RoundedRectangle(width=3.4, height=3.2, corner_radius=0.22, stroke_color=CYAN_D, stroke_width=1.6,
                                   fill_color=PANEL, fill_opacity=0.6)
            icon.move_to(box.get_center() + UP * 0.45)
            t = en(title, 30, INK, italic=False).move_to(box.get_center() + DOWN * 0.9)
            if t.width > 3.1: t.scale_to_fit_width(3.1)
            return VGroup(box, icon, t, shadow(box))
        ic1 = mono("( 3 + 4 ) × 2", 30, GOLD)
        p = VMobject(stroke_color=CYAN, stroke_width=2.6).set_points_as_corners([LEFT * 1.1, LEFT * 0.2, UP * 0.45 + RIGHT * 0.6])
        q = DashedLine(LEFT * 0.2, DOWN * 0.45 + RIGHT * 0.6, stroke_color=DIM, stroke_width=2.2)
        x = Cross(scale_factor=0.09, stroke_color=CRIMSON, stroke_width=3).move_to(UP * 0.45 + RIGHT * 0.66)
        back = CurvedArrow(UP * 0.3 + RIGHT * 0.45, UP * 0.15 + LEFT * 0.35, angle=-PI / 2, stroke_color=GOLD, stroke_width=2.2, tip_length=0.14)
        ic2 = VGroup(p, q, x, back)
        ic3 = VGroup(*[RoundedRectangle(width=1.5, height=0.32, corner_radius=0.06, stroke_color=c, stroke_width=1.8)
                       for c in (GOLD, CYAN, CYAN_D)]).arrange(DOWN, buff=0.06)
        cards = VGroup(card(ic1, "Expression evaluation"), card(ic2, "Backtracking"),
                       card(ic3, "Memory management")).arrange(RIGHT, buff=0.5).move_to(UP * 0.45)
        self.rig.update(x=0, y=0.1, w=FW)
        self.cam(x=0, y=0.05, w=13.8, dur=5.0)
        with self.beat("a1", hold=7.2):
            for k, c in enumerate(cards):
                self.sfx("click", -4)
                inner = c[1]
                anims = [FadeIn(c[3], shift=UP * 0.3), FadeIn(c[0], shift=UP * 0.3), sweep(c[0], GOLD, 3, 0.9), FadeIn(c[2], shift=UP * 0.2)]
                if k == 0: anims.append(Write(inner))
                elif k == 1: anims.append(AnimationGroup(Create(p), Create(q), FadeIn(x), Create(back), lag_ratio=0.3))
                else: anims.append(LaggedStart(*[FadeIn(r, shift=DOWN * 0.4) for r in reversed(inner)], lag_ratio=0.3))
                self.play(*anims, run_time=1.0)
            self.wait(1.2)
            self.cam(x=0, y=0.1, w=FW * 0.98, dur=1.8)
            self.wait(1.0)
            self.play(*[sweep(c[0], CYAN, 3, 1.0) for c in cards], run_time=1.0)
        self.outro()


# ================================================================ 04 array or linked list
class S04_Choice(DSAScene):
    def construct(self):
        self.chapter(4, "选型", "Array or linked list?")
        q = en("Recall: why don't we usually implement a list with an array?", 32, INK).move_to(UP * 2.45)
        cw = [1.7, 1.2, 3.3, 3.3]; rh = 0.62; ex = 0.42
        xs = np.cumsum([0] + cw) - sum(cw) / 2
        y0 = 1.75
        ys = [y0 - r * rh for r in range(5)] + [y0 - 5 * rh - ex]
        grid = VGroup()
        for r, y in enumerate(ys):
            x_start = xs[1] if r in (2, 3) else xs[0]
            grid.add(Line([x_start, y, 0], [xs[-1], y, 0], stroke_color=CYAN_D if r in (0, 1, 5) else FAINT, stroke_width=1.4))
        for k, x in enumerate(xs):
            if k == 1: grid.add(Line([x, ys[1], 0], [x, ys[4], 0], stroke_color=FAINT, stroke_width=1.4))
            else: grid.add(Line([x, ys[0], 0], [x, ys[5], 0], stroke_color=CYAN_D if k in (0, 4) else FAINT, stroke_width=1.4))
        def cc(r, c, span=1):
            return np.array([(xs[c] + xs[c + span]) / 2, (ys[r] + ys[r + 1]) / 2, 0])
        T = VGroup(en("Topic", 28, SOFT, italic=False).move_to(cc(0, 0, 2)),
                   en("Array", 28, CYAN, italic=False).move_to(cc(0, 2)),
                   en("Linked List", 28, CYAN, italic=False).move_to(cc(0, 3)),
                   en("Efficiency", 28, SOFT, italic=False).move_to(np.array([(xs[0] + xs[1]) / 2, (ys[1] + ys[4]) / 2, 0])),
                   *[mono(op, 22, INK).move_to(cc(1 + i, 1)) for i, op in enumerate(["push", "pop", "top"])],
                   en("Space", 28, SOFT, italic=False).move_to(cc(4, 0, 2)))
        qm = VGroup(*[mono("?", 24, DIM).move_to(cc(r, c)) for r in (1, 2, 3, 4) for c in (2, 3)])
        with self.beat("c1"):
            self.play(FadeIn(q, shift=DOWN * 0.15), run_time=0.6)
            self.play(Create(grid), run_time=1.0)
            self.play(FadeIn(T), LaggedStart(*[FadeIn(m, scale=1.4) for m in qm], lag_ratio=0.08),
                      *[sweep(l, GOLD, 3, 0.9) for l in grid[:2]], run_time=1.0)
        self.think(2.0, pos=RIGHT * 5.5 + UP * 0.5)
        tag = self.answer_tag(UP * 1.45 + RIGHT * 5.55)
        self.play(FadeIn(tag), run_time=0.35)
        # demos below the table: camera pans down
        D = DOWN * 9.0
        vals = ["a", "b", "c", "d", "e"]
        cells = VGroup(*[Cell(v, 1.0, 0.7, font="serif", size=26) for v in vals]).arrange(RIGHT, buff=0.12).move_to(D + UP * 1.3 + LEFT * 0.6)
        slot6 = slot(1.0, 0.7).next_to(cells, RIGHT, buff=0.12)
        sub1 = en("List in an array: insert into the middle", 26, SOFT).next_to(cells, UP, buff=0.4)
        self.cam(y=D[1] - 0.45, dur=1.3)
        with self.beat("c2"):
            self.play(FadeIn(cells, lag_ratio=0.1), FadeIn(slot6), FadeIn(sub1), run_time=0.8)
            self.sfx("whoosh", -9)
            self.play(LaggedStart(*[cells[k].animate.shift(RIGHT * 1.12) for k in (4, 3, 2)], lag_ratio=0.25), run_time=1.0)
            xx = Cell("x", 1.0, 0.7, color=GOLD, font="serif", size=26).move_to(cells[1].get_center() + RIGHT * 1.12 + UP * 1.0)
            self.sfx("push", 0, at=0.4)
            self.play(xx.animate.shift(DOWN * 1.0), run_time=0.5)
            self.play(burst(xx.get_center(), GOLD, 10, 0.5, 0.4), run_time=0.4)
            o_n = VGroup(mono("O(n)", 26, CRIMSON), en("shifting", 24, CRIMSON)).arrange(RIGHT, buff=0.15).next_to(cells, DOWN, buff=0.35)
            self.play(FadeIn(o_n), run_time=0.4)
        arr = VGroup(*[Cell(v, 1.0, 0.7, font="serif", size=26) for v in "abc"]).arrange(RIGHT, buff=0.12).move_to(D + DOWN * 1.0 + LEFT * 1.17)
        free = VGroup(*[slot(1.0, 0.7) for _ in range(3)]).arrange(RIGHT, buff=0.12).next_to(arr, RIGHT, buff=0.12)
        sub2 = en("Stack: one end only", 26, GOLD).next_to(arr, DOWN, buff=0.35).align_to(arr, LEFT)
        def at(r, c): return cc(r, c)
        o1 = VGroup(*[mono("O(1)", 24, GOLD).move_to(at(r, c)) for r in (1, 2, 3) for c in (2, 3)])
        with self.beat("c3"):
            self.play(FadeIn(arr), FadeIn(free), FadeIn(sub2), run_time=0.5)
            d = Cell("d", 1.0, 0.7, color=GOLD, font="serif", size=26).move_to(free[0].get_center() + UP * 0.9)
            self.add(d)
            self.sfx("push", 0, at=0.4)
            self.play(d.animate.move_to(free[0]), run_time=0.45)
            self.sfx("pop", 0, at=0.05)
            self.play(d.animate.shift(UP * 0.9).fade(1), burst(free[0].get_center(), CYAN, 10, 0.5, 0.4), run_time=0.45)
            ok = VGroup(mono("O(1)", 26, GOLD), en("no shifting", 24, GOLD)).arrange(RIGHT, buff=0.15).next_to(sub2, RIGHT, buff=0.5)
            self.play(FadeIn(ok), run_time=0.3)
            self.cam(y=0.35 - 0.45, dur=1.2)
            self.wait(1.2)
            self.sfx("chime", -4)
            self.play(*[FadeOut(m) for m in qm[:6]],
                      LaggedStart(*[FadeIn(o, scale=1.3) for o in o1], lag_ratio=0.12), run_time=1.0)
        self.remove(cells, slot6, sub1, xx, o_n, arr, free, sub2, ok, d)
        sp1 = VGroup(en("fixed size", 24, INK), en("may waste space or fill up", 20, SOFT)).arrange(DOWN, buff=0.06).move_to(at(4, 2))
        sp2 = VGroup(en("grows on demand", 24, INK), en("+ one pointer per node", 20, SOFT)).arrange(DOWN, buff=0.06).move_to(at(4, 3))
        with self.beat("c4"):
            self.play(FadeOut(qm[6]), FadeIn(sp1, shift=UP * 0.1), run_time=0.5)
            self.play(FadeOut(qm[7]), FadeIn(sp2, shift=UP * 0.1), run_time=0.5)
        col = RoundedRectangle(width=cw[2] - 0.08, height=ys[0] - ys[5] - 0.08, corner_radius=0.08, stroke_color=GOLD,
                               stroke_width=2.2).move_to(np.array([(xs[2] + xs[3]) / 2, (ys[0] + ys[5]) / 2, 0]))
        with self.beat("c5"):
            self.cam(x=col.get_center()[0] * 0.3, w=13.2, dur=1.6)
            self.sfx("chime_lo", -3)
            self.play(Create(col), run_time=0.7)
            self.play(sweep(col, HOT, 4, 0.8), run_time=0.8)
        self.outro()


# ---------------------------------------------------------------- shared code (verbatim)
CTOR = ["public Stack(int size) {",
        "    values = new Double[size];",
        "    top = -1;",
        "}"]
PUSH = ["public Double push(double x) {",
        "    if(isFull())",
        "        return null;",
        "    values[++top] = Double.valueOf(x);",
        "    return top();",
        "}"]
DISPLAY = ["public void displayStack() {",
           '    System.out.print("top -->");',
           "    for(int i =top; i >= 0; i --)",
           '      System.out.println("\\t|\\t " + ',
           '        String.format("%, .4f",values[i].doubleValue()) +',
           '        "\\t|");',
           '    System.out.println("\\t+-----------------------+");',
           "}"]
MAIN = ["public static void main(String[] args) {",
        "    Stack myStack = new Stack(4);",
        "    System.out.println(myStack.isEmpty());",
        "    myStack.push(-3);",
        "    myStack.push(5);",
        '    System.out.println("The stack has 2 items:");',
        "    myStack.displayStack();",
        "    myStack.push(1);",
        "    myStack.push(2);",
        "    myStack.push(-1);",
        '    System.out.println("The stack has 4 items:");',
        "    myStack.displayStack();",
        '    System.out.println("The top is: " + myStack.top());',
        "    System.out.println(myStack.isFull());",
        "    myStack.pop();",
        "    myStack.pop();",
        "    myStack.pop();",
        "    myStack.pop();",
        '    System.out.println("The stack is empty:");',
        "    myStack.displayStack();",
        "}"]

def jfmt(v):
    """Java String.format("%, .4f", v): ' ' flag pads non-negatives with a space."""
    s = f"{abs(v):,.4f}"
    return ("-" if v < 0 else " ") + s

def display_lines(vals_bottom_to_top):
    """Console rendering of displayStack() (tabs expanded to fixed columns)."""
    out = []
    for k, v in enumerate(reversed(vals_bottom_to_top)):
        pre = "top --> " if k == 0 else " " * 8
        out.append(pre + "|" + f"{jfmt(v):>15}" + " " * 8 + "|")
    base = "+" + "-" * 23 + "+"
    out.append(("top --> " if not vals_bottom_to_top else " " * 8) + base)
    return out

def fmt_val(v): return f"{float(v):.1f}"

# ================================================================ 05 array implementation
class S05_Implementation(DSAScene):
    def construct(self):
        self.chapter(5, "实现", "Array implementation")
        sv = StackView(self, 4, bottom=LEFT * 3.6 + DOWN * 1.85, w=1.5, h=0.56, gap=0.1, font_size=24,
                       index_labels=True, index_fmt="[{i}]", marker_value=True)
        vlab = VGroup(mono("values", 24, CYAN), mono(": Double[]", 20, DIM)).arrange(RIGHT, buff=0.08).next_to(sv.pos(3), UP, buff=0.55)
        c1 = VGroup(VGroup(mono("values", 30, CYAN), en("the array that holds the elements", 30, SOFT)).arrange(RIGHT, buff=0.3),
                    VGroup(mono("top", 30, GOLD), en("index of the top element", 30, SOFT)).arrange(RIGHT, buff=0.3)
                    ).arrange(DOWN, aligned_edge=LEFT, buff=0.35).move_to([-1.9, 1.0, 0], aligned_edge=LEFT)
        with self.beat("i1"):
            self.play(sv.build(), FadeIn(vlab), run_time=0.9)
            self.play(FadeIn(sv.marker, shift=RIGHT * 0.2), FadeIn(sv.mval), glow_in(c1[0], CYAN), run_time=0.7)
            self.play(glow_in(c1[1], GOLD), Indicate(sv.marker.lab, color=GOLD), run_time=0.7)
        # UML (verbatim)
        head = mono("Stack", 26, GOLD)
        fields = VGroup(mono("values: Double[]", 21), mono("top: int", 21)).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        meths = VGroup(*[mono(m, 21) for m in ["+ Stack(int size)", "+ isEmpty(): boolean", "+ isFull(): boolean",
                                                "+ top(): Double", "+ push(double x): Double", "+ pop(): Double",
                                                "+ displayStack():void"]]).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        W = max(fields.width, meths.width) + 0.7
        hb = Rectangle(width=W, height=0.62); fb = Rectangle(width=W, height=fields.height + 0.4); mb = Rectangle(width=W, height=meths.height + 0.4)
        boxes = VGroup(hb, fb, mb).arrange(DOWN, buff=0).set_stroke(CYAN_D, 1.6).set_fill(PANEL, 0.85)
        head.move_to(hb); fields.move_to(fb).align_to(fb, LEFT).shift(RIGHT * 0.35); meths.move_to(mb).align_to(mb, LEFT).shift(RIGHT * 0.35)
        uml = VGroup(boxes, head, fields, meths).move_to(RIGHT * 1.15 + UP * 0.6)
        note = en("Setters and getters are not listed.", 26, DIM).next_to(uml, DOWN, buff=0.15)
        dbl = VGroup(en("Double:", 28, GOLD), en("for demonstration", 26, GOLD)).arrange(DOWN, aligned_edge=LEFT, buff=0.08).next_to(uml, RIGHT, buff=0.35).align_to(uml, UP).shift(DOWN * 0.15)
        with self.beat("i2"):
            self.play(FadeOut(c1, shift=UP * 0.2), FadeIn(boxes, shift=UP * 0.2), FadeIn(head), sweep(boxes, GOLD, 3, 1.0), run_time=0.7)
            self.play(FadeIn(fields, shift=RIGHT * 0.1), FadeIn(dbl, shift=LEFT * 0.1), run_time=0.5)
            self.play(LaggedStart(*[FadeIn(m, shift=RIGHT * 0.1) for m in meths], lag_ratio=0.12), run_time=1.2)
            self.play(FadeIn(note), run_time=0.4)
        # constructor
        cp = CodePanel(CTOR, size=26, title="Stack.java").move_to(RIGHT * 1.9 + UP * 1.45)
        with self.beat("i3"):
            self.play(FadeOut(VGroup(uml, note, dbl), shift=RIGHT * 0.4), dissolve_particles([uml], RIGHT, 50, run_time=0.6), run_time=0.6)
            self.play(FadeIn(cp, shift=UP * 0.15), sweep(cp.box, CYAN, 3, 0.8), run_time=0.6)
            self.play(cp.highlight(1))
            self.sfx("click", -3)
            self.play(LaggedStart(*[pulse(s, CYAN, 1.15, 0.5) for s in sv.slots], lag_ratio=0.15), run_time=0.8)
            self.play(cp.highlight(2))
            self.sfx("chime_hi", -3)
            self.play(pulse(sv.marker.lab, GOLD, 1.6), Indicate(sv.mval, color=GOLD, scale_factor=1.3),
                      burst(sv.marker.dot.get_center(), GOLD, 10, 0.4, 0.6), run_time=0.8)
        why = en("Why  −1 ?", 44, GOLD).next_to(cp, DOWN, buff=0.5)
        with self.beat("i4"):
            self.play(glow_in(why, GOLD), run_time=0.6)
        self.think(2.0, pos=RIGHT * 5.4 + DOWN * 0.55)
        tag = self.answer_tag(RIGHT * 5.45 + DOWN * 0.55)
        a1 = VGroup(mono("top", 30, GOLD), en("= index of the top element", 32, INK)).arrange(RIGHT, buff=0.2)
        a2 = VGroup(en("empty stack has no top", 32, INK), mono("→  top = -1", 30, GOLD)).arrange(RIGHT, buff=0.25)
        ans = VGroup(a1, a2).arrange(DOWN, aligned_edge=LEFT, buff=0.3).next_to(cp, DOWN, buff=0.5).align_to(cp, LEFT)
        br = Brace(Line(sv.pos(0) + DOWN * 0.3, sv.pos(-1) + DOWN * 0.05), LEFT, color=GOLD).shift(LEFT * 0.6)
        with self.beat("i5"):
            self.play(FadeIn(tag), FadeOut(why), FadeIn(a1, shift=RIGHT * 0.1), run_time=0.5)
            self.play(FadeIn(a2, shift=RIGHT * 0.1), run_time=0.5)
            self.play(pulse(sv.marker, GOLD, 1.3), sweep(sv.bucket, GOLD, 4, 0.8), run_time=0.8)
        a3 = VGroup(VGroup(en("first push lands in", 30, SOFT), mono("values[0]", 28, CYAN)).arrange(RIGHT, buff=0.18),
                    VGroup(mono("top == -1", 28, GOLD), en("means the stack is empty", 30, SOFT)).arrange(RIGHT, buff=0.18)
                    ).arrange(DOWN, aligned_edge=LEFT, buff=0.25).next_to(ans, DOWN, buff=0.3).align_to(ans, LEFT)
        with self.beat("i6"):
            self.play(FadeIn(a3[0], shift=RIGHT * 0.1), run_time=0.5)
            ghost = sv.marker.copy().fade(0.5)
            self.play(ghost.animate.shift(sv._marker_delta(0)), Indicate(sv.idx[0], color=CYAN, scale_factor=1.4), run_time=0.7)
            self.play(FadeOut(ghost), FadeIn(a3[1], shift=RIGHT * 0.1), run_time=0.5)
        # push
        pp = CodePanel(PUSH, size=23.5, title="Stack.java").move_to(RIGHT * 2.1 + UP * 1.2)
        with self.beat("i7"):
            self.play(FadeOut(VGroup(ans, a3, tag), shift=DOWN * 0.2), FadeOut(cp, shift=UP * 0.2), FadeOut(cp.hl), run_time=0.5)
            self.play(FadeIn(pp, shift=UP * 0.15), sweep(pp.box, CYAN, 3, 0.8), run_time=0.6)
            self.play(pp.highlight(1, 2))
            chk = result_tag("isFull() → false", CYAN, 22, "").next_to(pp, DOWN, buff=0.4).align_to(pp, LEFT)
            self.play(FadeIn(chk, shift=RIGHT * 0.1), run_time=0.4)
        s1 = VGroup(mono("① ++top", 26, GOLD), mono("top: -1 → 0", 26, INK)).arrange(RIGHT, buff=0.45)
        s2 = mono("② values[0] = -3.0", 26, CYAN)
        steps = VGroup(s1, s2).arrange(DOWN, aligned_edge=LEFT, buff=0.28).next_to(pp, DOWN, buff=0.4).align_to(pp, LEFT)
        with self.beat("i8"):
            self.cam(x=0.25, y=0.2, w=13.6, dur=1.5)
            self.play(FadeOut(chk), pp.highlight(3))
            self.play(FadeIn(s1, shift=RIGHT * 0.1), run_time=0.4)
            self.sfx("tick", 0)
            self.play(*sv.marker_to(0, run_time=0.7), Indicate(pp.token(3, "++top"), color=GOLD, scale_factor=1.15), run_time=0.7)
            self.play(FadeIn(s2, shift=RIGHT * 0.1), run_time=0.4)
            sv.marker_to_done = True
            c = sv.make_cell("-3.0"); c.move_to(sv.pos(0)); c.save_state()
            src = s2[-4:]
            c.move_to(src.get_center()).scale(0.4).fade(1); self.add(c); sv._trail(c)
            self.sfx("push", 0, at=0.7)
            self.play(Restore(c, rate_func=rate_functions.ease_in_out_cubic, path_arc=0.6), Indicate(src, color=GOLD),
                      Succession(Wait(0.7), burst(sv.pos(0), GOLD, 12, 0.55, 0.5)), run_time=1.2)
            sv.cells.append(c); sv.top_index = 0
        with self.beat("i9"):
            self.cam(x=0, y=0, w=FW, dur=1.5)
            self.play(pp.highlight(4))
            r = result_tag("returns -3.0", GOLD, 24).next_to(steps, DOWN, buff=0.3).align_to(steps, LEFT)
            self.sfx("chime_hi", -3)
            self.play(FadeIn(r, shift=RIGHT * 0.1), pulse(c.rect), sweep(c.rect, GOLD, 4, 0.6), run_time=0.6)
        sv.clear_trails()
        self.outro()


# ================================================================ 06 displayStack
class S06_Display(DSAScene):
    def construct(self):
        self.chapter(6, "输出", "displayStack()")
        cp = CodePanel(DISPLAY, size=18, line_h=0.33, title="Stack.java")
        cp.move_to(LEFT * (6.27 - cp.box.width / 2) + UP * (2.6 - cp.box.height / 2))
        sv = StackView(self, 4, bottom=RIGHT * 4.7 + DOWN * 0.1, w=1.3, h=0.48, gap=0.08, font_size=20,
                       index_labels=True, index_fmt="i={i}", marker=True)
        con = Console(width=5.2, height=1.28, size=18)
        con.move_to([cp.box.get_left()[0] + con.box.width / 2, cp.box.get_bottom()[1] - 0.38 - con.box.height / 2, 0])
        lines = display_lines([-3, 5])
        with self.beat("p1"):
            self.play(FadeIn(cp, shift=UP * 0.15), sweep(cp.box, CYAN, 3, 0.8), sv.build(), run_time=0.8)
            self.play(FadeIn(sv.marker), run_time=0.3)
            for v in ("-3.0", "5.0"): sv.push(v, run_time=0.35, sfx=False)
            self.play(FadeIn(con, shift=UP * 0.1), run_time=0.4)
        first = con.make_line(lines[0][:7]); con.n -= 1
        with self.beat("p2"):
            self.cam(x=-0.3, y=0.05, w=13.6, dur=1.4)
            self.play(cp.highlight(1))
            self.sfx("type", 0)
            src = cp.token(1, '"top -->"')
            self.play(TransformFromCopy(src[1:-1], first), run_time=0.7)
        iv = mono("i = 1", 24, GOLD).next_to(sv.bucket, DOWN, buff=0.35)
        with self.beat("p3"):
            self.cam(x=0, y=0, w=FW, dur=1.2)
            self.play(cp.highlight(2), FadeIn(iv), run_time=0.4)
            self.play(pulse(sv.cells[1].rect), sweep(sv.cells[1].rect, GOLD, 4, 0.5), run_time=0.5)
            self.play(cp.highlight(3, 5))
            l0 = con.make_line(lines[0]); self.sfx("type", 0)
            self.play(FadeOut(first, run_time=0.01), con._type(l0), run_time=0.5)
            self.play(cp.highlight(2), Transform(iv, mono("i = 0", 24, GOLD).move_to(iv)), run_time=0.4)
            self.play(pulse(sv.cells[0].rect), sweep(sv.cells[0].rect, GOLD, 4, 0.5), run_time=0.5)
            self.play(cp.highlight(3, 5))
            l1 = con.make_line(lines[1]); self.sfx("type", 0)
            self.play(con._type(l1), run_time=0.5)
        fmt = VGroup(mono('"%, .4f"', 28, GOLD), en("4 decimal places", 26, INK),
                     en("a space before positives,", 24, SOFT), en("so they line up with negatives", 24, SOFT)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        fmt.next_to(con, RIGHT, buff=0.45).align_to(con, UP)
        with self.beat("p4"):
            self.focus(VGroup(con.box, fmt), margin=0.5, dur=1.4)
            self.play(cp.highlight(4), FadeIn(fmt, shift=LEFT * 0.1), run_time=0.5)
            self.play(Indicate(l0, color=GOLD, scale_factor=1.04), Indicate(l1, color=GOLD, scale_factor=1.04), run_time=0.9)
        with self.beat("p5"):
            self.cam(x=0, y=0, w=FW, dur=1.2)
            self.play(FadeOut(fmt), cp.highlight(6), Transform(iv, mono("i = -1  → exit", 24, DIM).move_to(iv)), run_time=0.5)
            l2 = con.make_line(lines[2]); self.sfx("type", 0)
            self.play(con._type(l2), run_time=0.4)
            self.play(sweep(sv.bucket, CYAN, 4, 0.7), run_time=0.6)
        sv.clear_trails()
        self.outro()


# ================================================================ 07 demo main()
class S07_Demo(DSAScene):
    def step(self, i, j=None):
        self.play(self.cp.highlight(i, j), run_time=0.35)

    def out(self, s, color=None):
        self.sfx("type", 0)
        self.play(self.con.print(s, color, run_time=0.28))
        self.printed.append(s)

    def construct(self):
        self.printed = []
        self.chapter(7, "演示", "Demo · main()")
        intro = VGroup(en("Tracing a complete main()", 46, INK), spaced("STEP BY STEP", 16, GOLD, 3.0)).arrange(DOWN, buff=0.3)
        with self.beat("m0"):
            self.play(glow_in(intro[0], GOLD), FadeIn(intro[1]), run_time=0.8)
        self.cp = cp = CodePanel(MAIN, size=15, line_h=0.236, title="Main.java", pad=0.18)
        cp.move_to(LEFT * (6.27 - cp.box.width / 2) + UP * (3.03 - cp.box.height / 2))
        self.con = con = Console(width=4.4, height=6 * 0.237 + 0.5, size=15, max_lines=6)
        con.move_to(RIGHT * 4.05 + DOWN * 1.22)
        con.title.align_to(con.box, RIGHT).shift(LEFT * 0.12)   # keep the label clear of the stack pointer
        sv = StackView(self, 4, bottom=RIGHT * 3.55 + UP * 0.40, w=1.2, h=0.44, gap=0.06, font_size=19,
                       index_labels=True, index_fmt="{i}", marker=True, marker_value=True)
        self.chapter_end()
        self.play(FadeOut(intro, shift=UP * 0.3), dissolve_particles([intro], UP, 50, run_time=0.6), run_time=0.6)
        self.play(FadeIn(cp, shift=RIGHT * 0.2), sweep(cp.box, CYAN, 3, 0.9), FadeIn(con), run_time=0.7)
        with self.beat("m1"):
            self.step(1)
            self.play(sv.build(), run_time=0.7)
            self.play(FadeIn(sv.marker), FadeIn(sv.mval), run_time=0.4)
        with self.beat("m2"):
            self.step(2); self.out("true")
        with self.beat("m3"):
            self.step(3); sv.push(fmt_val(-3), run_time=0.6, from_mob=cp.token(3, "-3"), path_arc=-0.4)
            self.step(4); sv.push(fmt_val(5), run_time=0.6, from_mob=cp.token(4, "5"), path_arc=-0.4)
        with self.beat("m4"):
            self.step(5); self.out("The stack has 2 items:")
            self.step(6)
            for l in display_lines([-3, 5]): self.out(l)
        with self.beat("m5"):
            self.step(7); sv.push(fmt_val(1), run_time=0.5, from_mob=cp.token(7, "1"), path_arc=-0.4)
            self.step(8); sv.push(fmt_val(2), run_time=0.5, from_mob=cp.token(8, "2"), path_arc=-0.4)
        with self.beat("m6"):
            self.step(9)
            self.cam(x=0.3, y=0.1, w=13.9, dur=1.0)
            e = sv.reject(fmt_val(-1), from_mob=cp.token(9, "-1"))
            nl = result_tag("null", CRIMSON, 20).next_to(e, RIGHT, buff=0.25)
            self.play(FadeIn(nl), run_time=0.35)
            self.play(e.animate.shift(UP * 0.5).fade(1), FadeOut(nl), run_time=0.6)
            self.remove(e)
        with self.beat("m7"):
            self.cam(x=0, y=0, w=FW, dur=1.0)
            self.step(10); self.out("The stack has 4 items:")
            self.step(11)
            for l in display_lines([-3, 5, 1, 2]): self.out(l)
        with self.beat("m8"):
            self.step(12)
            self.sfx("chime_hi", -3)
            ghost = sv.cells[-1].label.copy()
            self.play(pulse(sv.cells[-1].rect, CYAN), ghost.animate(path_arc=0.5).move_to(con.box.get_bottom() + UP * 0.4 + RIGHT * 0.3).fade(1),
                      run_time=0.7)
            self.out("The top is: 2.0")
        with self.beat("m9"):
            self.step(13); self.out("true")
        olab = spaced("POP ORDER", 12, DIM, 2.6).move_to(RIGHT * 5.55 + UP * 2.95)
        with self.beat("m10"):
            self.play(FadeIn(olab), run_time=0.25)
            for k in range(4):
                self.step(14 + k)
                slot_pt = RIGHT * 5.55 + UP * (2.55 - k * 0.42)
                c = sv.pop(run_time=0.5, to_point=slot_pt, fade=False)
                t = mono(["2.0", "1.0", "5.0", "-3.0"][k], 19, GOLD).move_to(slot_pt)
                self.play(FadeOut(c), FadeIn(t), run_time=0.2)
        with self.beat("m11"):
            self.play(pulse(sv.marker, GOLD, 1.3), Indicate(sv.mval, color=GOLD), run_time=0.6)
            self.step(18); self.out("The stack is empty:")
            self.step(19)
            for l in display_lines([]): self.out(l)
        sv.clear_trails()
        # the complete output, all in one place
        full = Console(width=5.8, height=len(self.printed) * 15 * 0.0158 + 0.55, size=15, title="COMPLETE OUTPUT")
        full.move_to(UP * 0.4)
        for l in self.printed: full.lines.add(full.make_line(l))
        tick = VMobject(stroke_color=GREEN, stroke_width=6).set_points_as_corners([LEFT * 0.22 + UP * 0.02, LEFT * 0.05 + DOWN * 0.17, RIGHT * 0.25 + UP * 0.25])
        tick.next_to(full.box, RIGHT, buff=0.4)
        with self.beat("m12", hold=7.4):
            mobs = self.content()
            self.sfx("whoosh", -6)
            self.play(*[FadeOut(m) for m in mobs], dissolve_particles(mobs, RIGHT, 60, run_time=0.7), run_time=0.7)
            self.rig.update(w=FW * 0.97)
            self.cam(w=FW, dur=3.0)
            self.play(FadeIn(full.box, shift=UP * 0.2), FadeIn(full.title), FadeIn(full.submobjects[0]), run_time=0.5)
            self.play(LaggedStart(*[Console._type(l) for l in full.lines], lag_ratio=0.12), run_time=1.6)
            self.sfx("chime_lo", 0)
            self.play(sweep(full.box, GOLD, 3, 0.9), FadeIn(tick, scale=1.4), burst(tick.get_center(), GOLD, 14, 0.7, 0.7), run_time=0.9)
        self.outro()


# ================================================================ 08 summary + end card (knowledge points only)
class S08_Summary(DSAScene):
    def construct(self):
        self.chapter(8, "小结", "Summary")
        rows = [
            en("A stack inserts and deletes only at the top  —  LIFO", 44, INK),
            VGroup(mono("push · pop · top", 36, GOLD), en("plus", 40, SOFT), mono("isEmpty · isFull", 36, CYAN)).arrange(RIGHT, buff=0.3),
            VGroup(en("Array:", 42, INK), mono("top = -1", 36, GOLD), en("to start; push uses", 42, INK), mono("values[++top]", 36, GOLD)).arrange(RIGHT, buff=0.22),
            VGroup(en("Failures return", 42, INK), mono("null", 36, CRIMSON), en(": push when full, pop / top when empty", 42, INK)).arrange(RIGHT, buff=0.18),
        ]
        G = VGroup()
        for i, r in enumerate(rows):
            num = mono(f"{i + 1:02d}", 26, GOLD)
            G.add(VGroup(num, r).arrange(RIGHT, buff=0.4))
        G.arrange(DOWN, aligned_edge=LEFT, buff=0.62)
        if G.width > 12.0: G.scale_to_fit_width(12.0)
        G.move_to(UP * 0.4)
        for bid, idx, hd in (("s1", (0, 1), 9.2), ("s2", (2, 3), 8.0)):
            with self.beat(bid, hold=hd):
                for k in idx:
                    self.sfx("click", -4)
                    ln = Line(G[k].get_left() + DOWN * 0.32, G[k].get_right() + DOWN * 0.32, stroke_color=GOLD, stroke_width=2)
                    self.play(FadeIn(G[k], shift=RIGHT * 0.2), ShowPassingFlash(ln, time_width=0.5), run_time=0.7)
        # end card: shared lib layout (title, next episode, brand logo, credits)
        self.end_card("Stacks", "Queues", beat_id="e1")
