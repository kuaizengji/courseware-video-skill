"""English VO for an episode script: Gemini TTS first, local Kokoro as the automatic fallback.

  python $CVS_HOME/toolkit/lib/tts.py <episode_dir> [--provider auto|gemini|kokoro] (default from config: kokoro) [--voice ...] [--speed ...] [--asr]

Reads <episode_dir>/script.py (BEATS: id -> (zh, vo)); writes build/vo/<id>.wav (24 kHz mono, trimmed),
build/vo/durations.json (seconds + provider per line) and build/vo/provider.json (the episode's voice).

Provider order (--provider auto, the default):
  1. Gemini TTS, if the GEMINI_API_KEY environment variable is set (never stored in any file). Model / voice /
     speaking style come from config.json voice.gemini.* (default calm teacher tone).
  2. Kokoro (local, offline, Apache-2.0), voice config.json voice.name (default am_michael, speed 1.03).
One voice per episode: if Gemini fails on ANY line (no key, quota 429 after retries, API/network error), the whole
episode is (re)generated with Kokoro instead of mixing two voices. Lines are cached by text + provider + voice, so
re-runs only synthesise changed lines; switching provider re-synthesises every line.
--asr: transcribes every line with faster-whisper 'small.en' (optional extra: pip install faster-whisper)."""
import argparse, os, sys, json, re, hashlib, importlib.util
import numpy as np, soundfile as sf
SAY = {"LIFO": "lie-foe"}   # spoken-form overrides (text stays as written for captions/ASR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvs_config as C
MODEL, VOICES = C.KOKORO_MODEL, C.KOKORO_VOICES   # $CVS_MODELS or $CVS_HOME/models (install.sh downloads them)
VOICE = C.CONFIG.get("voice", {})
GEM = dict(model="gemini-3.8-flash-tts", voice="Charon", style="calm, warm, clear teacher tone, moderate pace",
           sample_rate=24000, retries=5)
GEM.update(VOICE.get("gemini", {}))


class TTSFail(Exception):
    pass


def gemini_tts(text, model, voice, style, retries=5):
    """One line via the Gemini API -> (float32 mono, sr). Raises TTSFail. Key only from env GEMINI_API_KEY."""
    import base64, time, io, requests
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key: raise TTSFail("GEMINI_API_KEY not set")
    H = {"x-goog-api-key": key, "Content-Type": "application/json"}
    base = "https://generativelanguage.googleapis.com/v1beta"

    def interactions():
        body = {"model": model, "input": [{"type": "user_input", "content": [{"type": "text", "text": text,
                "annotations": [{"type": "speech_metadata", "style": style}]}]}],
                "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": voice}]}}
        r = requests.post(f"{base}/interactions", headers=H, json=body, timeout=180)
        if r.status_code != 200: return None, r.status_code, r.text[:300]
        j = r.json(); data = None
        for st in j.get("steps", []):
            if st.get("type") == "model_output":
                for c in st.get("content", []):
                    if c.get("type") == "audio": data = c.get("data")
        if data is None and "output_audio" in j: data = j["output_audio"].get("data")
        return (base64.b64decode(data) if data else None), 200, "no audio in response"

    def generate_content():
        body = {"contents": [{"parts": [{"text": f"Say in a {style}: {text}"}]}],
                "generationConfig": {"responseModalities": ["AUDIO"],
                                     "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
        r = requests.post(f"{base}/models/{model}:generateContent", headers=H, json=body, timeout=180)
        if r.status_code != 200: return None, r.status_code, r.text[:300]
        try: p = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
        except (KeyError, IndexError): return None, 200, "no audio in response"
        return base64.b64decode(p["data"]), 200, ""

    calls = [interactions, generate_content] if "3.8" in model else [generate_content, interactions]
    code, info = None, ""
    for attempt in range(retries + 1):
        for fn in calls:
            try: audio, code, info = fn()
            except Exception as e: audio, code, info = None, -1, repr(e)[:200]
            if audio:
                if audio[:4] == b"RIFF":
                    x, sr = sf.read(io.BytesIO(audio), dtype="float32")
                    return (x.mean(1) if x.ndim == 2 else x), sr
                x = np.frombuffer(audio[: len(audio) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
                return x, int(GEM.get("sample_rate", 24000))
            if code in (400, 401, 403): raise TTSFail(f"Gemini HTTP {code}: {info}")   # bad key / request: no retry
            if code == 429 and re.search(r"per day|quota|retry in \d+h", info, re.I):
                raise TTSFail(f"Gemini quota exhausted: {info}")                         # daily quota: no point waiting
            if code == 404: continue                                                     # try the other endpoint
            break                                                                        # 429 / 5xx / network: back off
        if code in (429, 500, 502, 503, 504, -1) and attempt < retries:
            time.sleep(min(60, 5 * 2 ** attempt)); continue
        break
    raise TTSFail(f"Gemini failed (HTTP {code}): {info}")

def load_script(ep):
    spec = importlib.util.spec_from_file_location("script", os.path.join(ep, "script.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m.BEATS

def trim(x, sr, thr=0.004, pad=0.10):
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx): return x
    a = max(0, idx[0] - int(pad * sr)); b = min(len(x), idx[-1] + int(pad * 2 * sr))
    return x[a:b]

NUM = {"0":"zero","1":"one","2":"two","3":"three","4":"four","5":"five","6":"six","16":"sixteen","2.0":"two point oh"}
SYN = {"baseline":"base line","underflow":"under flow","y":"why","java":"dot java","stack.java":"stack dot java"}
def norm_words(s):
    s = s.lower()
    s = re.sub(r"\d+\.\d+|\d+", lambda m: " " + NUM.get(m.group(0), m.group(0)) + " ", s)
    s = re.sub(r"[^a-z0-9. ]", " ", s.replace("-", " "))
    s = " ".join(SYN.get(w.strip("."), w.strip(".")) for w in s.split())
    return s.replace("under flow", "underflow").replace("base line", "baseline").split()



def synth_episode(beats, out, meta, provider, voice, speed):
    """Synthesise every line that is not cached for this provider/voice. Raises TTSFail on the first failure."""
    k = None
    for bid, (zh, vo) in beats.items():
        tag = f"{provider}|{voice}|{GEM['model'] + '|' + GEM['style'] if provider == 'gemini' else speed}"
        h = hashlib.md5(f"{vo}{SAY}|{tag}".encode()).hexdigest()[:10]
        wav = os.path.join(out, bid + ".wav")
        if bid in meta and meta[bid].get("hash") == h and os.path.exists(wav): continue
        say = vo
        for kk, vv in SAY.items(): say = say.replace(kk, vv)
        if provider == "gemini":
            s, sr = gemini_tts(say, GEM["model"], voice, GEM["style"], int(GEM.get("retries", 5)))
        else:
            if k is None:
                if not (os.path.exists(MODEL) and os.path.exists(VOICES)):
                    raise SystemExit(f"Kokoro model missing in {os.path.dirname(MODEL)} - run install.sh (or set CVS_MODELS)")
                from kokoro_onnx import Kokoro
                k = Kokoro(MODEL, VOICES)
            s, sr = k.create(say, voice=voice, speed=speed, lang=VOICE.get("lang", "en-us"))
        s = trim(np.asarray(s, dtype=np.float32), sr)
        sf.write(wav, s, sr)
        meta[bid] = {"hash": h, "dur": round(len(s) / sr, 3), "text": vo, "provider": provider, "voice": voice}
        print(f"{bid:5s} {len(s)/sr:5.2f}s  [{provider}:{voice}]  {vo}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("ep")
    ap.add_argument("--provider", choices=["auto", "gemini", "kokoro"], default=VOICE.get("provider", "auto"),
                    help="auto = Gemini if GEMINI_API_KEY is set, else / on any failure Kokoro (whole episode)")
    ap.add_argument("--voice", default=None, help="Kokoro voice (default config voice.name = am_michael)")
    ap.add_argument("--gemini-voice", default=None, help="Gemini voice (default config voice.gemini.voice)")
    ap.add_argument("--speed", type=float, default=VOICE.get("speed", 1.03), help="Kokoro speed")
    ap.add_argument("--asr", action="store_true")
    a = ap.parse_args()
    ep = os.path.abspath(a.ep); out = os.path.join(ep, "build", "vo"); os.makedirs(out, exist_ok=True)
    beats = load_script(ep)
    meta_p = os.path.join(out, "durations.json")
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    kvoice = a.voice or VOICE.get("name", "am_michael")
    gvoice = a.gemini_voice or GEM["voice"]
    order = {"auto": ["gemini", "kokoro"], "gemini": ["gemini"], "kokoro": ["kokoro"]}[a.provider]
    if a.provider == "auto" and not os.environ.get("GEMINI_API_KEY", "").strip():
        print("GEMINI_API_KEY not set -> Kokoro"); order = ["kokoro"]
    used = None
    for prov in order:
        try:
            synth_episode(beats, out, meta, prov, gvoice if prov == "gemini" else kvoice, a.speed)
            used = prov; break
        except TTSFail as e:
            print(f"!! {prov} failed: {e}")
            if prov != order[-1]: print("!! regenerating the WHOLE episode with Kokoro (one voice per episode)")
            json.dump(meta, open(meta_p, "w"), indent=1)
    if used is None: raise SystemExit("TTS failed with every provider")
    for bid in list(meta):
        if bid not in beats: meta.pop(bid)
    json.dump(meta, open(meta_p, "w"), indent=1)
    json.dump({"provider": used, "voice": gvoice if used == "gemini" else kvoice,
               "model": GEM["model"] if used == "gemini" else "kokoro-v1.0"}, open(os.path.join(out, "provider.json"), "w"), indent=1)
    print("provider %s | total VO %.1fs, %d lines" % (used, sum(m["dur"] for m in meta.values()), len(meta)))
    if a.asr:
        from faster_whisper import WhisperModel
        from scipy.signal import resample_poly
        wm = WhisperModel("small.en", device="cpu", compute_type="float32")   # small.en fp32: far fewer hallucinations on short lines
        rep = []
        for bid, (zh, vo) in beats.items():
            x, sr = sf.read(os.path.join(out, bid + ".wav"))
            x = np.concatenate([np.zeros(sr // 2), x, np.zeros(sr // 2)])   # pad: whisper drops edges otherwise
            x = resample_poly(x, 2, 3).astype(np.float32)   # 24k -> 16k
            segs, _ = wm.transcribe(x, beam_size=5, condition_on_previous_text=False)
            hyp = " ".join(s.text.strip() for s in segs)
            ref_w, hyp_w = norm_words(vo), norm_words(hyp)
            ref_w = [w for w in ref_w if w not in ("and", "a", "the")]
            miss = [w for w in ref_w if w not in hyp_w]
            flag = "OK " if not miss else "CHK"
            rep.append(f"{flag} {bid:5s} REF: {vo}\n          ASR: {hyp}\n          missing: {miss}")
        open(os.path.join(out, "asr_report.txt"), "w").write("\n".join(rep) + "\n")
        print("\n".join(r for r in rep if r.startswith("CHK")))
