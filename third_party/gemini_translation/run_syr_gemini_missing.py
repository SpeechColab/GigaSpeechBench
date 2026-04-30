#!/usr/bin/env python3
"""Run Gemini on missing SYR segments for Low-Resource-Languages."""
import json, os, time, tempfile
from collections import defaultdict
from pydub import AudioSegment
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.0-flash"

BASE = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark"
REF_DIR = os.path.join(BASE, "Low-Resource-Languages/text/ref/SYR")
HYP_PATH = os.path.join(BASE, "Low-Resource-Languages/text/hyp/SYR_Gemini.json")
AUDIO_DIR = "/tmp/SYR_audio/SYR"
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

def transcribe(client, audio_path, start, end):
    audio = AudioSegment.from_file(audio_path)
    seg = audio[int(start*1000):int(end*1000)]
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    seg.export(tmp.name, format="wav")
    try:
        uploaded = client.files.upload(file=tmp.name)
        response = client.models.generate_content(
            model=MODEL,
            contents=["Transcribe the speech accurately.", uploaded],
        )
        try:
            client.files.delete(name=uploaded.name)
        except: pass
        return response.text.strip()
    finally:
        os.unlink(tmp.name)

def main():
    client = genai.Client(api_key=API_KEY)

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
        wav = os.path.join(AUDIO_DIR, aname+".wav")
        if not os.path.isfile(wav): continue
        for seg in d.get("segments",[]):
            if seg.get("status") == "invalid": continue
            key = (norm(aname), round(float(seg["start"]),2), round(float(seg["end"]),2))
            if key not in hyp_keys:
                missing.append((aname, float(seg["start"]), float(seg["end"]), wav))

    print(f"Missing: {len(missing)} segs", flush=True)
    added = 0
    errors = 0

    for aname, start, end, wav in missing:
        try:
            text = transcribe(client, wav, start, end)
            hyp.append({
                "audio_path": aname,
                "text": text,
                "language": "SYR",
                "model": "gemini-3-flash-preview",
                "start_time": start,
                "end_time": end,
            })
            added += 1
            if added % 20 == 0:
                with open(HYP_PATH,"w",encoding="utf-8") as f:
                    json.dump(hyp, f, ensure_ascii=False, indent=2)
                print(f"  [{added}/{len(missing)}] saved, errors={errors}", flush=True)
        except Exception as e:
            errors += 1
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = min(60, 15 * (errors % 5 + 1))
                print(f"  Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"  Error: {err[:80]}", flush=True)
                time.sleep(3)
        time.sleep(2)

    with open(HYP_PATH,"w",encoding="utf-8") as f:
        json.dump(hyp, f, ensure_ascii=False, indent=2)
    print(f"Done: +{added}, errors={errors}, total={len(hyp)}")

if __name__ == "__main__":
    main()
