#!/usr/bin/env python3
"""Bar grid for an episode timeline (default 120 BPM, 4/4 -> beat 0.5 s, bar 2.0 s).
  python grid_03a.py <stems>/timeline.json [--bpm 120] [--reveal m12] [--out grid.json]
(--bpm must match the score's tempo; --reveal = caption id of the hero reveal / climax.)
1) timeline-first plan: per-boundary padding (seconds to ADD, never cut) so every chapter head lands on a downbeat
   and every caption/shot change on a half-bar (1 s) -> future renders can be cut to the grid by construction.
2) fit-to-current: the single bar-grid phase offset that best matches the CURRENT cuts (used by score_v2.py)."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
import argparse
_ap = argparse.ArgumentParser(); _ap.add_argument("timeline"); _ap.add_argument("--bpm", type=float, default=120.0)
_ap.add_argument("--reveal", default="m12", help="caption id of the hero reveal (climax downbeat)")
_ap.add_argument("--out", default="grid.json")
_A = _ap.parse_args()
TL = _A.timeline
BPM = _A.bpm; BAR = 240.0 / BPM; HALF = BAR / 2
REVEAL_ID = _A.reveal


def main():
    d = json.load(open(TL))
    caps, chs = d["captions"], d["chapters"]
    bounds = []
    ch_t = {round(c["t"], 3): c for c in chs}
    for c in caps:
        t = round(c["t"], 3)
        kind = "chapter" if t in ch_t else ("reveal" if c.get("id") == REVEAL_ID else "shot")
        bounds.append(dict(t=c["t"], kind=kind, id=c.get("id") or "pause", en=c["en"][:50],
                           chapter=ch_t[t]["en"] if t in ch_t else None))
    bounds.sort(key=lambda b: b["t"])
    # ---- timeline-first padding (cumulative); shots quantised to a beat (plan) and to a half-bar (alt)
    def plan(shot_q):
        acc, rows = 0.0, []
        for b in bounds:
            q = BAR if b["kind"] in ("chapter", "reveal") else shot_q
            shifted = b["t"] + acc
            target = np.ceil(shifted / q - 1e-6) * q
            pad = target - shifted
            rows.append(dict(id=b["id"], kind=b["kind"], chapter=b["chapter"], t_now=round(b["t"], 3),
                             t_grid=round(float(target), 3), pad_before_s=round(float(pad), 3),
                             bar=int(target // BAR) + 1, beat_in_bar=int(round((target % BAR) / (BAR / 4))) + 1, text=b["en"]))
            acc += pad
        return acc, rows
    acc_half, _ = plan(HALF)
    acc, rows = plan(BAR / 4)
    end_now = d["duration"]
    end_grid = np.ceil((end_now + acc) / BAR) * BAR
    # ---- fit current timeline: phase offset phi (grid = phi + 2k) minimising distance of chapter cuts to downbeats
    cuts = [c["t"] for c in chs] + [b["t"] for b in bounds if b["kind"] == "reveal"]
    w = [1.0] * len(chs) + [2.0]
    best = None
    for phi in np.arange(0, BAR, 0.01):
        dist = [abs(((t - phi + BAR / 2) % BAR) - BAR / 2) for t in cuts]
        cost = sum(wi * di for wi, di in zip(w, dist))
        if best is None or cost < best[0]:
            best = (cost, phi, dist)
    _, phi, dist = best
    phi = round(float(phi), 2)
    fit = [dict(cut=round(t, 3), nearest_downbeat=round(phi + round((t - phi) / BAR) * BAR, 3),
                offset_s=round(float(t - (phi + round((t - phi) / BAR) * BAR)), 3)) for t in cuts]
    out = dict(bpm=BPM, meter="4/4", beat_s=BAR / 4, bar_s=BAR,
               timeline_first=dict(rule="chapter heads + reveal -> next downbeat (2 s); other caption/shot changes -> next beat (0.5 s); pad = hold added BEFORE the boundary (never cut)", total_padding_if_shots_on_half_bar_s=round(float(acc_half), 3),
                                   total_padding_s=round(float(acc), 3), duration_now=round(end_now, 3),
                                   duration_grid=round(float(end_grid), 3), bars=int(end_grid / BAR), boundaries=rows),
               fit_current=dict(phase_offset_s=phi, note="downbeats at phase_offset + 2k s; chapter changes snap to the nearest downbeat, hits stay on the exact cut",
                                cuts=fit, mean_abs_offset_s=round(float(np.mean([abs(f['offset_s']) for f in fit])), 3)))
    p = _A.out
    json.dump(out, open(p, "w"), indent=1, ensure_ascii=False)
    print("phase", phi, "mean |offset|", out["fit_current"]["mean_abs_offset_s"], "total pad", round(acc, 2))
    for r in rows:
        if r["pad_before_s"] > 0.001 or r["kind"] != "shot":
            print(f"  {r['id']:6s} {r['kind']:8s} now {r['t_now']:7.2f} -> {r['t_grid']:7.2f}  pad +{r['pad_before_s']:.2f}  bar {r['bar']} beat {r['beat_in_bar']}")
    for f in fit: print("  fit", f)


if __name__ == "__main__":
    main()
