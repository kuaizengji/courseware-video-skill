# courseware-video-skill

**Agent skill + toolkit: turn course slides into cinematic teaching videos** — Manim animation, original code-generated music, local TTS narration and bilingual captions.

[中文说明](#中文说明) · MIT licensed (logo excluded, see [Licences](#licences--credits))

## What it does

Give an AI agent (or yourself) a folder of course materials — `.pptx`, `.ppt`, `.pdf`, `.docx` — and this skill turns each file into a polished explainer video:

- **Teaching episodes** (default route, one per lecture/tutorial): step-by-step Manim animation on a light, premium-looking theme; English male voiceover (local Kokoro `am_michael`); bilingual captions on every shot (Chinese line that may explain more + English line matching the VO); dark code cards with the current line highlighted; full worked traces with console output; ~4–6 min each.
- **Course intro / promo films** (for a course-introduction deck or a trailer): no voiceover — music, SFX and bilingual captions only; dark glowing code-drawn visuals, cuts on the beat, cold open → title card → build → climax at ~70–90 % → quick recap → end card.
- **Original music written as code** for every video: one continuous piece per video with its own key, progression, tempo and motif; the bed is an original soft pad in the style of the linear-algebra promo's bed (re-struck each bar on the chord), harmonized with the episode's lead and SFX; no bass (low end only from kick and impacts); layers switch per section, beat-less stretches under dense explanation, near-silences before "pause & think" moments, a 0.4 s dead stop before the reveal, climax on the result, piano recap. Mastered to −16 LUFS, music ducked under the voice.
- **Content rules baked in**: knowledge points only (no homework/grading/admin), no visible trace of the source slides (no slide numbers, course codes, screenshots), unanswered questions become a "Pause & think" beat followed by a reference answer, no invented code.
- **QA tooling**: contact sheets, caption/VO checks, safe-margin edge scanner, loudness and true-peak checks.

## Repository layout

| Path | What |
|---|---|
| `SKILL.md` | The workflow as an agent skill (front-matter + rules). Load it into any agent that supports skills / system instructions. |
| `install.sh` | Idempotent installer: apt deps → Python venv (pinned) → Kokoro model → Salamander piano SF2 → fonts → smoke test. |
| `toolkit/lib/` | Style library for Manim (`dsa_style.py`), post-production (captions, picture, stems), mixing, QA, edge scan, SFX, TTS. |
| `toolkit/music/` | Score engine (`score_v4.py`, `scorecfg.py`, `pads.py`, `bed.py`, `grid_03a.py`, `analyze.py`, `engine/`). |
| `toolkit/assets/` | Fonts (OFL), caption plates, SFX bank, default brand logo. |
| `toolkit/smoke/` | End-to-end smoke test (3 s scene + caption + music bed + one TTS line → MP4). |
| `example/03a_stacks/` | A complete finished teaching episode ("Stacks"): `script.py`, `scenes.py`, `music.json`, `render.sh`. |

## Requirements

Debian/Ubuntu (tested on Debian 13, Python 3.13), `sudo` for apt, internet for the first install, ~3 GB disk. CPU only — no GPU and no API keys needed.

## Install

```bash
git clone https://github.com/kuaizengji/courseware-video-skill.git
cd courseware-video-skill
bash install.sh                       # installs into $HOME/courseware-video by default
source ~/courseware-video/env.sh
```

`install.sh` is safe to re-run. It downloads (and sha256-checks) the Kokoro-82M ONNX model (~350 MB) from the official kokoro-onnx release and the Salamander Grand Piano SF2 from FreePats (310 MB download, 1.27 GB unpacked); neither is stored in this repo. Takes ~10–20 min, mostly downloads.

Switches: `CVS_HOME=/path` (install location), `CVS_SKIP_APT=1`, `CVS_SKIP_SMOKE=1`, `CVS_SF2=/existing/Salamander.sf2` (reuse a local copy).

## Quick start

Render the example episode (full 1080p30 pipeline):

```bash
source ~/courseware-video/env.sh
cd $CVS_HOME/example/03a_stacks
bash render.sh                 # Q="-ql" for a fast low-res draft, J=<parallel jobs>
# -> out/stacks_VO.mp4, out/stacks_noVO.mp4, out/stacks_contact.png
```

Make your own episode:

1. Convert the source file to PDF + per-slide PNGs and extract the text (`libreoffice --headless`, `pdftoppm`, python-pptx / python-docx).
2. Create a project folder outside the toolkit, e.g. `my-course-videos/ep/01_intro/`, and copy the example layout:
   - `script.py` — beats: `id -> (Chinese caption, English VO line)`
   - `scenes.py` — Manim scenes using `with self.beat("id"): ...`
   - `music.json` — this episode's key, tempo, progression, motif, bed and cue sheet
   - `render.sh` — the pipeline: TTS → Manim → `post.py` → `grid_03a.py` → `score_v4.py` → mux → `qa.py`
3. Audition the music first: `python $CVS_HOME/toolkit/music/bed.py --seconds 20 --music-config music.json --out audition.wav`.
4. QA: `qa.py sheet|caps|loud`, `edgescan.py` (80 px safe margin).

## Configuration

Copy overrides into `$CVS_HOME/config.json` (created from `toolkit/config.default.json` at install; partial files are merged):

| Key | Default | Meaning |
|---|---|---|
| `brand.enabled` | `true` | `false` hides logo and "Powered by" on the end card |
| `brand.logo_light` / `brand.logo_dark` | Kuaizengji logo | SVG for light / dark themes (relative to `toolkit/assets/`) — **replace with your own brand** |
| `brand.site` | `www.kuaizengji.com` | "Powered by …" line; `""` hides it |
| `voice.provider` | `kokoro` | `kokoro` (local, default), `auto` or `gemini` (needs `GEMINI_API_KEY` in the environment, never in a file) |
| `voice.name` / `voice.speed` | `am_michael` / `1.03` | Kokoro voice |
| `theme` | `light` | `light` for teaching, `dark` for promo films (env `DSA_THEME` wins) |
| `music.pad` | `X2` | fallback bed timbre only — each episode should design its own bed in `music.json` |

Path variables: `CVS_HOME`, `CVS_MODELS`, `CVS_SF2`, `CVS_CONFIG`, `CVS_PROJECT`.

If Gemini TTS is selected and fails (no key, quota, API error), the **whole episode** falls back to Kokoro, so one episode never mixes two voices.

## Using it as an agent skill

`SKILL.md` is a self-contained skill file (YAML front-matter `name` / `description` + the workflow). To use it:

- **Agents with a skills folder** (e.g. Claude Code `~/.claude/skills/courseware-video/SKILL.md`, or any agent framework that loads `SKILL.md` files): copy `SKILL.md` into a `courseware-video/` skill folder.
- **Other agents**: paste `SKILL.md` into the system prompt / project instructions.

Then ask the agent something like: *"Turn every file in ./lectures into teaching videos with the courseware-video skill; do lecture 1 first as a pilot."* The skill tells the agent to ingest the materials, write an outline, pilot one episode, iterate with you, and log decisions before batching the rest. The toolkit is the optional reference implementation the skill uses when it is installed.

## Licences & credits

Some rule ideas (pacing floor, retell test, delivery gate, doctor, pitfalls log) adapted from [liyupi/ai-promo-video-maker](https://github.com/liyupi/ai-promo-video-maker) (MIT).

- **Code, scripts, docs, example episode**: MIT — © 2026 Jimmy Xu / 快增绩 Kuaizengji. See `LICENSE` and `NOTICE`.
- **Kuaizengji (快增绩) name and logo** (`toolkit/assets/brand/`): **trademarks, excluded from the MIT licence.** They ship only as the default end-card brand. Set your own brand in `config.json` (or `brand.enabled: false`) before publishing videos.
- **Salamander Grand Piano** (Alexander Holm; SF2 by FreePats.org): CC BY 3.0 — credit required. The end card prints it; also put it in video descriptions: `Piano samples: "Salamander Grand Piano" by Alexander Holm, CC BY 3.0 (SF2 version by FreePats.org).`
- **Kokoro-82M** model & **kokoro-onnx**: Apache-2.0 / MIT.
- **Fonts** Inter, JetBrains Mono, Cormorant Garamond (bundled with their `OFL.txt`), Noto Serif CJK (apt): SIL OFL 1.1.
- **Manim Community**: MIT. Other libraries/programs keep their own licences.

Full list: [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). All music material, pads, bass, arps, drums and SFX are generated by this toolkit's own code; no third-party songs, loops or samples other than the Salamander piano are used.

---

## 中文说明

**一个 Agent 技能 + 工具包：把课程课件（PPT / PDF / Word）做成电影感的讲解视频。** Manim 动画、代码生成的原创配乐、本地 TTS 配音、中英双语字幕。

### 能做什么
- **教学片**（默认，每讲一集）：Manim 逐步动画讲解，浅色高级感画面；英文男声配音（本地 Kokoro `am_michael`）；每个镜头都有双语字幕（上面中文可多解释，下面英文与配音一致）；代码卡片逐行高亮，完整演示程序执行和输出；每集约 4–6 分钟。
- **课程介绍片 / 宣传片**：不配音，只有音乐、音效和双语字幕；深色发光画面，卡拍快剪，高潮在全片 70–90% 处。
- **原创配乐（用代码写）**：每支视频一首连贯的曲子，调性、和弦、速度、动机按这一集的内容单独设计；铺底统一采用仿「线性代数宣传片」风格的原创柔和 pad（每小节随和弦重新起音），并和这一集的旋律、音效配成和谐的一套；全程不用贝斯（低频只留底鼓和重击）；讲解密集处无节拍，"暂停思考"前近乎静音，揭晓前 0.4 秒全停，高潮落在结果揭晓，钢琴回顾收尾。母带 −16 LUFS，配音时音乐自动压低。
- **内容规则**：只讲知识点（不含作业、评分等事务性内容）；画面里看不出课件痕迹；没有答案的问题先"暂停思考"再给参考答案；不编造课件里没有的代码。

### 安装
```bash
git clone https://github.com/kuaizengji/courseware-video-skill.git
cd courseware-video-skill
bash install.sh                 # 默认装到 $HOME/courseware-video
source ~/courseware-video/env.sh
```
安装脚本可重复运行：装系统依赖 → 建 Python 虚拟环境（锁定版本）→ 下载并校验 Kokoro 模型（约 350 MB）和 Salamander 钢琴音源（解压后 1.27 GB）→ 安装字体 → 跑冒烟测试。模型和音源不放在仓库里。只需 CPU，不需要任何 API key。

### 快速上手
- 渲染范例：`cd $CVS_HOME/example/03a_stacks && bash render.sh`
- 做自己的一集：在工具包外建项目文件夹（如 `my-course-videos/ep/01/`），照范例写 `script.py`（中文字幕 + 英文配音）、`scenes.py`、`music.json`、`render.sh`。

### 作为 Agent 技能使用
把 `SKILL.md` 放进你的 Agent 的技能目录（如 `courseware-video/SKILL.md`），或者直接贴进系统提示词。然后对它说："用 courseware-video 技能把 ./lectures 里的课件都做成教学视频，先做第一讲当试点。"

### 配置与品牌
在 `$CVS_HOME/config.json` 里改品牌、配音、主题等（见上方英文表格）。**快增绩的名称和 logo 是商标，不在 MIT 授权范围内**，只作为默认片尾品牌附带；发布你自己的视频前，请在 `config.json` 里换成你自己的品牌，或设 `brand.enabled: false`。

### 许可
部分规则思路参考 [liyupi/ai-promo-video-maker](https://github.com/liyupi/ai-promo-video-maker)（MIT）。
代码、脚本、文档和范例：MIT（© 2026 Jimmy Xu / 快增绩 Kuaizengji）。Salamander 钢琴音源为 CC BY 3.0，必须署名（片尾已带）。字体为 SIL OFL 1.1。详见 `LICENSE` 和 `THIRD_PARTY_LICENSES.md`。
