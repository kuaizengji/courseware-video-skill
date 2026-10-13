# DECISIONS — <project>

Copy this file to the project root as DECISIONS.md at ingest. Keep "Series spec" and "Key table" current; append
dated decisions and one Retro per episode below them.

## Series spec
- Routes: teaching episodes (<list>) · intro/promo film (<yes/no>)
- Voice: <e.g. Kokoro am_michael, speed 1.03, English>; never mix voices within an episode
- Captions: bilingual (zh line + en line); full-width ｛ ｝ and plain-digit subscripts in zh lines; all in-scene text English
- Look: <theme>; ≥80 px safe margins
- Music: original per video, own key/mode/tempo/motif (see Key table); bed: <module>; NO bass/drone, bed HPF ~150 Hz
- Master: -16 LUFS, true peak < -1 dBTP; metadata = title only
- End card: <brand logo + "Powered by <site>"> + music credit
- Forbidden on screen/VO: <course codes, school, staff, admin> (pass extra words to `qa.py gate --forbid`)
- Delivery: <resolution/fps, naming, deliver/ copy, backup>
- Decided by the user / decided by us: <list what the user wants to hear about; default = we decide>

## Key table
| id | key | mode | bpm |
|---|---|---|---|
| <EP01> | <D> | <major> | <104> |

## Log
- <YYYY-MM-DD>: <decision> (<who>)

### <EPxx> Retro
- Feedback: <user's words>
- Changed: <what>
- Rule / pitfall added: <SKILL.md section or PITFALLS.md row, or "none">
