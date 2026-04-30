#!/usr/bin/env python3
"""
Run qwen3.5-omni-flash on common-voice using ThreadPoolExecutor for parallel API calls.
"""
import json, os, time, subprocess, tempfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import dashscope

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
API_KEY = os.getenv("DASHSCOPE_API_KEY")
MODEL = "qwen3.5-omni-flash"
MAX_WORKERS = 10
BASE = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark"

lock = threading.Lock()
rate_limiter = threading.Semaphore(MAX_WORKERS)


def norm(a):
    b = os.path.basename(str(a).replace("\\", "/"))
    while True:
        ch = False
        for e in [".wav", ".mp3", ".mp4", ".webm"]:
            if b.lower().endswith(e): b = b[:-len(e)]; ch = True
        if not ch: break
    if b.endswith("#raw"): b = b[:-4]
    return b


def find_audio(aname, lang):
    audio_root = f"{BASE}/common-voice/audio"
    for c in [f"{lang}/{aname}", f"{lang}/{aname}.wav", f"{lang}/{aname}.mp3"]:
        p = os.path.join(audio_root, c)
        if os.path.isfile(p): return p
    return None


def transcribe_one(aname, start, end, audio_path, lang):
    """Cut segment and transcribe. Returns (aname, start, end, text) or None."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-ss", str(start), "-to", str(end),
                     "-ac", "1", "-ar", "16000", tmp.name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for attempt in range(5):
            try:
                r = dashscope.MultiModalConversation.call(
                    api_key=API_KEY, model=MODEL,
                    messages=[{"role": "user", "content": [
                        {"audio": tmp.name},
                        {"text": "Transcribe this audio accurately."}
                    ]}],
                    result_format="message",
                )
                if r.status_code == 200:
                    text = r.output.get("choices", [{}])[0].get("message", {}).get("content", [{}])[0].get("text", "")
                    return (aname, start, end, text)
                elif r.status_code == 429:
                    wait = min(10 * (attempt + 1), 60)
                    time.sleep(wait)
                else:
                    return None
            except Exception:
                time.sleep(5)
                if attempt >= 2:
                    return None
    finally:
        os.unlink(tmp.name)
    return None


def run_language(lang, ref_dir, hyp_path):
    # Load existing
    hyp = json.load(open(hyp_path)) if os.path.exists(hyp_path) else []
    hyp_keys = set()
    for x in hyp:
        a = norm(x.get("audio_name", ""))
        s = round(float(x.get("start", x.get("start_time", 0))), 2)
        e = round(float(x.get("end", x.get("end_time", 0))), 2)
        hyp_keys.add((a, s, e))

    # Collect missing
    missing = []
    for rf in sorted(os.listdir(ref_dir)):
        if not rf.endswith(".json"): continue
        d = json.load(open(os.path.join(ref_dir, rf)))
        aname = d.get("audio_name", "")
        ap = find_audio(aname, lang)
        if not ap: continue
        for seg in d.get("segments", []):
            if seg.get("status") == "invalid": continue
            st, en = float(seg["start"]), float(seg["end"])
            if (norm(aname), round(st, 2), round(en, 2)) not in hyp_keys:
                missing.append((aname, st, en, ap))

    if not missing:
        print(f"{lang}: already complete ({len(hyp)} segs)", flush=True)
        return

    print(f"{lang}: {len(missing)} missing, {MAX_WORKERS} threads", flush=True)
    added = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(transcribe_one, aname, st, en, ap, lang): (aname, st, en)
            for aname, st, en, ap in missing
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                aname, st, en, text = result
                with lock:
                    hyp.append({
                        "audio_name": aname,
                        "text": text,
                        "language": lang,
                        "model": MODEL,
                        "start_time": st,
                        "end_time": en,
                    })
                    added += 1
                    if added % 200 == 0:
                        with open(hyp_path, "w") as f:
                            json.dump(hyp, f, ensure_ascii=False, indent=2)
                        print(f"  {lang}: {added}/{len(missing)}", flush=True)
            else:
                errors += 1

    with open(hyp_path, "w") as f:
        json.dump(hyp, f, ensure_ascii=False, indent=2)
    print(f"{lang}: DONE +{added} err={errors} total={len(hyp)}", flush=True)


def main():
    langs = ["KOR", "VNM", "IDN", "AR", "JPN", "THA"]  # small first
    for lang in langs:
        ref_dir = f"{BASE}/common-voice/text/ref/{lang}"
        hyp_path = f"{BASE}/common-voice/text/hyp/{lang}_{MODEL}.json"
        if not os.path.isdir(ref_dir):
            print(f"{lang}: no ref dir, skip", flush=True)
            continue
        run_language(lang, ref_dir, hyp_path)


if __name__ == "__main__":
    main()
