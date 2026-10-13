# Pitfalls (courseware-video)

Every entry happened on a real project. Check here first when something looks odd. When an episode ships, distil any new
problem from the project's DECISIONS.md into the right table below (project log -> generic pitfall, never the reverse).
Keep entries generic: no course codes, school names, data-set origins, people or local machine details.

## Captions & text

| Pitfall | Symptom | Fix |
|---|---|---|
| ASCII braces in Chinese captions | ASS treats `{...}` as an override block: "{A, B}⁺" showed only "⁺" | Use full-width ｛ ｝ in zh captions; `qa.py gate --captions` flags ASCII braces on CJK lines |
| Unicode subscripts in Chinese captions | Subscript glyphs missing / tofu in the CJK font | Write plain digits in zh captions (R1, not R₁); keep real subscripts only in English scene text |
| Text overflows its card | A long all-caps heading ran 40–50 px past the card edge | Size every card in a row from the widest heading (uniform width, centred row); run `qa.py boxes` per scene; scan cards in the final video too |
| Pseudocode too long for the card | Loop / end-if lines forced a tiny mono font | Drop pure-syntax lines (end for / end if), keep mono ≥ 22 px |
| Courseware leaks | "last lecture", "exercise of the last lecture", lab numbers in VO/captions | Rephrase ("Say we model…", "Next: <topic>"); `qa.py gate` greps captions for trace words |
| Material typos and variable clashes | Pseudocode reused a variable name; misspelt keywords | Fix silently, log it in DECISIONS |
| Concept used before it is defined | The material used a term slides before defining it | One-line definition at first use (see SKILL.md §1); retell test catches the rest |

## Picture

| Pitfall | Symptom | Fix |
|---|---|---|
| Content in the safe margin | Panels within 40–80 px of the frame edge | `edgescan.py` (light theme only; dark promo frames are all flagged), then judge each range by eye |
| Generated images carry marks | Native image generation added corner marks / logo-like stamps | Cover or crop them before use; check all four corners |

## Music

| Pitfall | Symptom | Fix |
|---|---|---|
| Low drone / bass | Listener found the low drone ugly | No bass line, no drone; high-pass the bed ~150 Hz; low end only from kick/impacts |
| Two videos in the same key | Parallel workers picked the same tonic+mode → re-score | Keep a fixed-format Key table in DECISIONS.md, reserve before scoring; `qa.py gate --keys DECISIONS.md --ep <id>` = ERROR on clash |
| Ran out of major/minor keys | All 24 tonic+mode pairs taken in a long series | Use church modes (Dorian, Lydian, Mixolydian…) and unused tempos |
| Endless timbre auditions | Many rounds of A/B on the bed sound | One batched audition round with short excerpts (SKILL.md §7) |

## Environment

| Pitfall | Symptom | Fix |
|---|---|---|
| Machine restart wipes system state | After a restart, system packages, database data dir, /tmp, venv and build/ intermediates were gone; some hosts restore project folders in the background, so they can look empty for a while | Don't panic or re-render; run the doctor (`--check`) first, then the idempotent rebuild script; keep finals in `deliver/` |
| Heavy parallel encodes | Shared machine ran out of memory | ffmpeg ≤ 2 threads under `nice`; render one scene at a time |

## Delivery

| Pitfall | Symptom | Fix |
|---|---|---|
| Large file transfers fail | Copies over ~100–256 MB failed; parallel copies made the target machine unreachable | Copy one file at a time; split or share big files another way |
| `~` in a Windows destination path | Created a literal "~" folder | Use absolute paths |
