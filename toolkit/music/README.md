# Score engine (original music written as code)

| file | role |
|---|---|
| `score_v4.py` | **the episode score engine**: one continuous piece driven by the episode timeline (stems from `lib/post.py`) — bed + per-section layers, near-silences, 0.4 s dead stop, build → climax on the reveal, piano recap, tonic-major ending, timeline SFX; writes music / sfx / noVO / VO masters (-16 LUFS) + plan.json |
| `scorecfg.py` | per-episode parameters (key, bpm, progression, motif, pad, cue sheet) — JSON via `--music-config`, CLI overrides |
| `bed.py` | short audition / music bed with the same parameters (used by the smoke test) |
| `grid_03a.py` | bar grid for a timeline (`--bpm`, `--reveal`): phase offset that best puts chapter cuts on downbeats + padding plan for timeline-first edits |
| `pads.py` | bed timbres `X X1 X2 X3 A B C D` |
| `score_v2.py`, `score_v3.py` | helper libraries imported by v4 (drums, bass, plucks, bells, piano via FluidSynth, SFX bank, mastering). Their own `main()` are earlier superseded score versions kept for reference. |
| `engine/dsp.py`, `engine/theory.py` | DSP (oscillators, filters, reverb IR, risers) and theory (chord symbols, voicing, `Note:beats` bar parser) |
| `analyze.py` | QA: LUFS / true peak / clipping / silence / band balance / spectrogram |

Typical episode run:
```bash
python grid_03a.py <stems>/timeline.json --bpm 100 --reveal <caption id> --out build/grid.json
python score_v4.py --stems <stems> --grid build/grid.json --outdir build/score --music-config music.json
python analyze.py build/score/music.wav
```
Piano = Salamander Grand Piano SF2 (`$CVS_SF2` or `$CVS_HOME/soundfonts/…`, CC BY 3.0, credit required).
