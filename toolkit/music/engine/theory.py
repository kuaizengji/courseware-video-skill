"""Tiny music-theory helpers: note names, chord symbols, voice leading."""
import itertools
import re

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def note(name):
    m = re.fullmatch(r"([A-G])([b#]?)(-?\d)", name)
    if not m:
        raise ValueError(name)
    pc = PC[m.group(1)] + {"": 0, "b": -1, "#": 1}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + pc


def pc_of(name):
    return (PC[name[0]] + {"": 0, "b": -1, "#": 1}[name[1:]]) % 12


def nname(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


QUAL = {
    "": [0, 4, 7], "m": [0, 3, 7], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "7": [0, 4, 7, 10],
    "sus4": [0, 5, 7], "sus2": [0, 2, 7], "add9": [0, 4, 7, 2], "madd9": [0, 3, 7, 2],
    "m9": [0, 3, 7, 10, 2], "maj9": [0, 4, 7, 11, 2], "7sus4": [0, 5, 7, 10], "6": [0, 4, 7, 9],
}


def chord(sym):
    """returns (root_pc, [pcs in priority order], bass_pc)"""
    m = re.fullmatch(r"([A-G][b#]?)([a-z0-9]*)(?:/([A-G][b#]?))?", sym)
    if not m:
        raise ValueError(sym)
    root = pc_of(m.group(1))
    ivs = QUAL[m.group(2)]
    pcs = [(root + i) % 12 for i in ivs]
    bass = pc_of(m.group(3)) if m.group(3) else root
    return root, pcs, bass


def in_range(pc, lo, hi):
    return [m for m in range(lo, hi + 1) if m % 12 == pc]


def voice(pcs, lo, hi, k, prev=None, avoid_low_thirds=True):
    """choose k notes in [lo,hi] covering as many chord pcs as possible (root/3rd/7th priority), closest to prev."""
    cands = [m for m in range(lo, hi + 1) if m % 12 in pcs]
    need = set(pcs[: min(k, len(pcs))])
    # prefer covering 3rd and 7th/9th; root optional when k < len(pcs)
    best, bestc = None, 1e9
    for combo in itertools.combinations(cands, k):
        got = {c % 12 for c in combo}
        miss = len(need - got)
        # avoid seconds in low register / minor 2nds anywhere
        s = sorted(combo)
        pen = 0
        for a, b in zip(s, s[1:]):
            if b - a == 1:
                pen += 6
            if b - a == 2 and a < 60:
                pen += 3
            if b - a <= 4 and a < 52 and avoid_low_thirds:
                pen += 4
        if prev:
            ps = sorted(prev)
            mv = sum(abs(a - b) for a, b in zip(s, ps[: len(s)]))
        else:
            mv = abs(sum(s) / k - (lo + hi) / 2)
        cost = miss * 20 + pen + mv * 0.6
        if cost < bestc:
            bestc, best = cost, list(s)
    return best


def parse_bar(s, default_beats):
    """'A4:1 D5:1 r:2' -> [(midi or None, start, dur)]; 'Asus4:2 A:2' -> chord list; plain 'Dm' -> whole bar"""
    items = []
    t = 0.0
    for tok in s.split():
        if ":" in tok:
            a, d = tok.split(":")
            d = float(d)
        else:
            a, d = tok, default_beats
        items.append((a, t, d))
        t += d
    return items


def scale_pcs(tonic, mode):
    steps = {"aeolian": [0, 2, 3, 5, 7, 8, 10], "ionian": [0, 2, 4, 5, 7, 9, 11], "lydian": [0, 2, 4, 6, 7, 9, 11]}[mode]
    return [(tonic + s) % 12 for s in steps]
