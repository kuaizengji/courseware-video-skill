"""Smoke-test scene (~3-4 s): one beat with a bilingual caption, a code card and a stack push, plus the brand logo."""
import sys, os
EP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(EP, "..", "lib"))
from dsa_style import *
DSABase.load_episode(EP)


class Smoke(DSAScene):
    def construct(self):
        title = spaced("COURSEWARE VIDEO", 40, INK, 1.8).move_to(UP * 2.0)
        sub = en("install check", 30, GOLD).next_to(title, DOWN, buff=0.25)
        logo = brand_logo(0.6)
        with self.beat("s1"):
            self.sfx("swell", -6)
            self.play(FadeIn(title, shift=UP * 0.2), FadeIn(sub), run_time=0.8)
            cells = VGroup(*[Cell(str(v), 1.1, 0.55) for v in (3, 1, 4)]).arrange(RIGHT, buff=0.12).move_to(DOWN * 0.3)
            for c in cells:
                self.sfx("push", -4)
                self.play(FadeIn(c, shift=DOWN * 0.3), burst(c.get_center(), GOLD, 8, 0.4, 0.3), run_time=0.35)
            if logo is not None:
                self.play(FadeIn(logo.next_to(cells, DOWN, buff=0.45)), run_time=0.4)
