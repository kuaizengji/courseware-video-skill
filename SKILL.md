---
name: courseware-video
description: >-
  Use this when turning course materials (slides, PDFs, docs) into polished
  explainer videos: step-by-step teaching episodes (Manim animation + English VO
  + bilingual captions + code-generated score) or a no-voiceover course
  intro/promo film.
---
# Courseware → video (teaching episodes + course intro film)

Two routes share one pipeline. Decide per file:
- **Teaching episode** (default for every lecture/tutorial): explain knowledge points step by step.
- **Intro / promo film** (only for a course-introduction deck, or when asked for a course trailer): make people want to learn; no step-by-step.

Optional reference implementation: the open-source courseware-video toolkit (https://github.com/kuaizengji/courseware-video-skill). If it is installed (`bash install.sh`, default `CVS_HOME=$HOME/courseware-video`, then `source $CVS_HOME/env.sh`), use it: `toolkit/lib/` = style (`dsa_style.py`) + post + mix + QA + edge scan + SFX + TTS (local Kokoro by default, Gemini optional); `toolkit/music/score_v4.py` + `scorecfg.py` + `pads.py` = the score engine, parameterised per episode (`--music-config music.json`: key, progression, tempo, motif, pad, cue sheet; `bed.py` for quick auditions); `toolkit/config.default.json` -> copy overrides into `$CVS_HOME/config.json` (brand logo/site, voice, theme); `example/03a_stacks/` = a finished episode (script.py, scenes.py, music.json, render.sh). Start each course in its own project folder (e.g. `<course>-videos/ep/<id>/`), copying the example episode layout; never edit the toolkit for one course. Without the toolkit, the rules below still apply with any Manim + ffmpeg + TTS setup.

## 0. Ingest
1. Convert every file to PDF (libreoffice headless; .ppt→.pptx first) and per-slide PNGs (pdftoppm). Extract text slide by slide incl. speaker notes and verbatim code (python-pptx / python-docx); describe figure-only slides by looking at the PNGs.
2. Write an OUTLINE: per file, knowledge points in order, which need animated step-by-step traces, code language, estimated length, admin-only slides, missing answers, typos.
3. Ask the user only real content questions (admin slides, blank answers); otherwise use the defaults below.
4. Copy `DECISIONS_TEMPLATE.md` (in the repo / `$CVS_HOME`) to the project as DECISIONS.md and fill in its **Series spec** and **Key table** before the first episode; every worker reads the Series spec first.

## 1. Content rules (both routes)
- Faithful to the material. Never invent code that isn't in it; animate behaviour instead.
- Knowledge points only: no homework, lab tasks, grading, deadlines, staff contacts.
- Viewers must NOT be able to tell any courseware exists: no 'slide N', no slide screenshots, no lecture numbers, course codes or school names; use 'Next: <topic>'.
- Unanswered questions / blank tables: pose it, ~2 s 'Pause & think' beat, then a labelled 'Reference answer' (standard, correct).
- Fix obvious typos silently.
- Terms at first use: when the material uses a term it never defines, give a one-line definition the first time it appears (short English label on screen; the Chinese caption may add a clause). Only for undefined terms in the material; do not add new content.

## 2. Teaching route
- **Look:** light theme (pale cool-gray gradient, navy text, indigo/blue primary, amber highlight, crimson errors, soft glows + shadows); dark code cards with the current line highlighted. Desktop/tablet first (ignore phone). Keep ≥80 px safe margins at all times (run the edge scanner).
- **Language:** ALL in-scene text English (labels, callouts, tables, titles, chapter labels). Bottom captions bilingual on every shot: Chinese line (may explain more) + English line beneath matching the VO.
- **Voiceover:** English male narrator, local Kokoro `am_michael` (speed ~1.03) by default. Gemini TTS is optional only if the user explicitly wants it and has a billed key (free tier is ~10 requests/day, not enough for one episode); never mix voices within an episode.
- **Motion:** every shot moves with purpose — camera follows the action, values fly from code into cells, light trails, small particle bursts on push/pop, smooth highlight slides, chapter transitions. Pacing tight (~4–6 min/episode).
- **Pacing floor** (so text can be read): a card with text holds ≥1.3 s after it lands; staggered items ≥0.3 s apart and the full set holds ≥0.8 s more; a push-in across several focus points gives each ≥1.4 s (not counting the move); the same layout at most 2 shots in a row; pure transitions ≤0.6 s. Do NOT apply promo density rules (≤4 s per scene, new event every 2 s) to teaching: full step-by-step traces and the beat-less/near-silent music stretches stay.
- **Structure:** title → chapters (definition → operations → applications/choices → implementation → full worked trace with console output) → short summary → end card.

## 3. Intro / promo route
- NO voiceover: music + SFX + bilingual captions only.
- Follow code-generated promo refs: dark background, one or two accent colours, glowing code-drawn diagrams/particles, 1 caption line + 1–3 labels per frame, title card at ~12–22 s, cold-open hook (single image growing, or quick montage + question), emotional build, climax at ~70–90% of runtime, quick beat-length recap, title/end card. Shots ~2.5–8 s, cuts on the beat.
- Hook fast: the cold open shows the problem or the core payoff within 3 s; first high-energy moment (music lift + title/claim) within 5 s. Pacing floor from §2 still applies.
- Style sample (non-blocking): before building, pick the direction yourself (consider at least one non-default idea, not only dark + glow), make ONE 16:9 style frame and show it in the first progress update; keep going unless the user objects. No course codes or school names on it; cover any marks a generated image carries.

## 4. Music (both routes; written as code, original)
- One continuous piece per video: one key family, one fixed round tempo (e.g. 120 BPM, bar = 2 s), never restarted at chapters. A sustained bed runs the whole time; layers (kick/bass/arps/bells/theme) switch on and off per section, mostly at cuts.
- Teaching: beat-less stretches (bed + in-key SFX) under dense explanation; groove only in operation/code sections; near-silences before turns ('pause & think', errors); 0.4 s dead stop before the hero reveal; build through the final worked trace; climax on the result reveal; piano recap; tonic-major ending. Music ducked ~-10 dB under VO.
- One melodic idea developed throughout (never stitch different themes); drops land on the tonic, prepared by a 1-bar dropout + riser + reversed in-key swell; no foreign timbres at the climax; no tempo bending.
- NO BASS: no bass line and no low drone in the bed (high-pass the bed ~150 Hz); the low end comes only from kick and impacts.
- Timbres: Salamander piano (CC BY 3.0, credit) + code-synthesised pads/arps/SFX; avoid GM orchestral sounds.
- BED STYLE (fixed for the series): every bed is an ORIGINAL imitation of the linear-algebra promo's bed (github.com/guchang233/linear-algebra-promo, no licence: study its sound and method, never copy code/notes): a soft synthesised pad re-struck every bar/4 s on the chord, same register, brightness and envelope character. Use the shared LA-style bed module (`toolkit/music/bed_la.py`, if present; otherwise write one following the same idea) and vary per episode only key, chord progression, voicing and motif. Each episode still gets its own key, progression, tempo and motif; the bed must harmonize with the episode's lead/arp/SFX as one palette (same key/chords, matching brightness/texture, complementary bands, no clashing timbres; check by spectrum).
- SFX generated from the same timeline, in key, quiet (clicks must never be loud); no noise whooshes on every cut.
- Timeline-first: one timeline file drives both animation and score; snap chapter heads to downbeats (pad holds, never cut content).
- Master -16 LUFS, true peak < -1 dBTP. You cannot listen: verify technically, then let the user judge by ear; offer short A/B excerpts rather than full re-renders.

## 5. End card & metadata
- Shared end card: topic title, 'NEXT · <topic>', the brand logo + 'Powered by <site>' if the user has one, small music credit ('Original score composed for this series. Piano samples: "Salamander Grand Piano" by Alexander Holm, CC BY 3.0 (SF2 version by FreePats.org). Other sounds synthesised in code.').
- Strip metadata except title.

## 6. QA before delivery
- Run the delivery gate first and fix every ERROR: `python $CVS_HOME/toolkit/lib/qa.py gate <video> --captions <zh/en srt|ass> --keys DECISIONS.md --ep <id> --edgescan --sheet <contact.jpg> [--forbid <course code> <school> ...]` (run under `nice`, ffmpeg ≤2 threads; exit 1 = ERROR). It checks spec, loudness/true peak, metadata, render log, ASCII braces in zh captions, courseware-trace words, key-table clashes, safe margins (WARN) and writes a contact sheet you must look at. Before a session or after a restart run the toolchain doctor (`bash $CVS_HOME/toolkit/doctor.sh`, check-only) and re-run `install.sh` only if something is MISSING.
- Retell test: read only the VO script; each chapter must be retellable in one sentence, and no concept may be used before it is explained. Fix the script, not the captions.
- Frame per caption at full res: no overlaps, tofu, cropped panels, half-faded captions; edge scan; caption ↔ VO match; courseware-trace grep (slide/lecture/课件/school) over captions, SRT, VO script, end card; loudness; frame count; A/V sync on SFX.
- Keep a second copy of finals in a `deliver/` folder (working output folders can get wiped or overwritten).

## 7. Workflow with the user
- Pilot one short episode first, iterate to approval, log every decision in DECISIONS.md, then batch the rest.
- Send finished MP4s as attachments; separate noVO/VO versions only while VO is undecided.
- Default: decide yourself. Only what the user must hear (voice, bed sound, score style) goes to them, batched into ONE audition round of 10–20 s A/B excerpts; never a blocking sign-off gate.
- After each episode add a 3-line Retro to DECISIONS.md (feedback → change → rule/pitfall). Check `PITFALLS.md` (in the repo / `$CVS_HOME`) when something looks odd; after delivery distil new generic pitfalls into it.
- Some rule ideas (pacing floor, retell test, delivery gate, doctor, pitfalls log) adapted from liyupi/ai-promo-video-maker (MIT).
