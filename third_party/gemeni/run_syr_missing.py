#!/usr/bin/env python3
"""Run Gemini on missing SYR segments (Low-Resource-Languages)."""
import json, os, time, tempfile
from collections import defaultdict
from pydub import AudioSegment
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"
OUTPUT_MODEL = "gemini-3-flash-preview"  # match existing hyp model field

BASE = "/path/to/dataset"
REF_DIR = os.path.join(BASE, "Low-Resource-Languages/text/ref/SYR")
HYP_PATH = os.path.join(BASE, "Low-Resource-Languages/text/hyp/SYR_Gemini.json")
AUDIO_DIR = "/path/to/SYR/audio"
TOL = 0.1

def norm(a):
    b = os.path.basename(str(a).replace("\\","/"))
    while True:
        ch=False
        for e in [".wav",".mp3",".mp4",".webm"]:
            if b.lower().endswith(e): b=b[:-len(e)]; ch=True
        if not ch: break
    if b.endswith("#raw"): b=b[:-4]
    return b

client = genai.Client(api_key=API_KEY)

def transcribe(audio_path, start, end):
    audio = AudioSegment.from_file(audio_path)
    seg = audio[int(start*1000):int(end*1000)]
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    seg.export(tmp.name, format="wav")
    try:
        uploaded = client.files.upload(file=tmp.name)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=["Transcribe the speech accurately.", uploaded],
        )
        try:
            client.files.delete(name=uploaded.name)
        except: pass
        return response.text.strip()
    finally:
        os.unlink(tmp.name)

def main():
    hyp = json.load(open(HYP_PATH))
    hyp_keys = set()
    for x in hyp:
        a = norm(x.get("audio_name") or x.get("audio_path",""))
        s = round(float(x.get("start",x.get("start_time",0))),2)
        e = round(float(x.get("end",x.get("end_time",0))),2)
        hyp_keys.add((a,s,e))

    missing = []
    for rf in sorted(os.listdir(REF_DIR)):
        if not rf.endswith('.json'): continue
        d = json.load(open(os.path.join(REF_DIR, rf)))
        aname = d.get("audio_name","")
        audio_path = os.path.join(AUDIO_DIR, aname + ".wav")
        if not os.path.isfile(audio_path):
            audio_path = os.path.join(AUDIO_DIR, aname.replace("#","_") + ".wav")
        if not os.path.isfile(audio_path):
            continue
        for seg in d.get("segments",[]):
            if seg.get("status") == "invalid": continue
            start, end = float(seg["start"]), float(seg["end"])
            if (norm(aname), round(start,2), round(end,2)) not in hyp_keys:
                missing.append((aname, start, end, audio_path))

    print(f"Missing: {len(missing)} segs", flush=True)
    added = 0
    errors = 0

    for aname, start, end, audio_path in missing:
        for attempt in range(5):
            try:
                text = transcribe(audio_path, start, end)
                hyp.append({
                    "audio_path": audio_path,
                    "text": text,
                    "language": "SYR",
                    "model": OUTPUT_MODEL,
                    "start_time": start,
                    "end_time": end,
                })
                added += 1
                if added % 10 == 0:
                    with open(HYP_PATH, "w", encoding="utf-8") as f:
                        json.dump(hyp, f, ensure_ascii=False, indent=2)
                    print(f"  [{added}/{len(missing)}] saved", flush=True)
                break
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    wait = min(30 * (2**attempt), 300)
                    print(f"  Rate limited, wait {wait}s", flush=True)
                    time.sleep(wait)
                else:
                    errors += 1
                    print(f"  Error: {err[:80]}", flush=True)
                    time.sleep(3)
                    break
        time.sleep(4)  # ~15 RPM

    with open(HYP_PATH, "w", encoding="utf-8") as f:
        json.dump(hyp, f, ensure_ascii=False, indent=2)
    print(f"Done: +{added}, errors={errors}, total={len(hyp)}")

if __name__ == "__main__":
    main()
