#!/usr/bin/env python3
"""
Run gpt-4o-transcribe on missing fleurs segments.
"""
import json, os, time, tempfile
from collections import defaultdict
from pydub import AudioSegment
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-transcribe"

BASE = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark"
REF_ROOT = os.path.join(BASE, "fleurs/text/ref")
HYP_DIR = os.path.join(BASE, "fleurs/text/hyp")
AUDIO_ROOTS = [
    os.path.join(BASE, "fleurs/audio/testbatch"),
    os.path.join(BASE, "fleurs/audio/batch_1"),
    os.path.join(BASE, "fleurs/audio/batch_2"),
    os.path.join(BASE, "fleurs/audio"),
]

LANG_MAP = {
    "EGY": "ar", "IDN": "id", "JPN": "ja", "KOR": "ko",
    "MYS": "ms", "PHL": "fil", "THA": "th", "VNM": "vi",
}
TOL = 0.1

def norm(a):
    b = os.path.basename(str(a).replace("\\","/"))
    while True:
        ch=False
        for e in [".wav",".mp3",".mp4",".webm"]:
            if b.lower().endswith(e): b=b[:-len(e)]; ch=True
        if not ch: break
    return b

def find_audio(aname, lang):
    for root in AUDIO_ROOTS:
        for wav in [f"{lang}/{aname}.wav", f"{lang}/{aname}.mp3", f"{aname}.wav"]:
            p = os.path.join(root, wav)
            if os.path.isfile(p): return p
    return None

def transcribe(client, audio_path, start, end, lang_code):
    audio = AudioSegment.from_file(audio_path)
    seg = audio[int(start*1000):int(end*1000)]
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    seg.export(tmp.name, format="wav")
    try:
        with open(tmp.name, "rb") as f:
            result = client.audio.transcriptions.create(
                model=MODEL, file=f, language=lang_code
            )
        return result.text.strip()
    finally:
        os.unlink(tmp.name)

def main():
    client = OpenAI(api_key=API_KEY)
    
    for lang in ["IDN", "KOR", "PHL", "THA", "VNM"]:
        hyp_path = os.path.join(HYP_DIR, f"{lang}_gpt4o-transcribe.json")
        ref_dir = os.path.join(REF_ROOT, lang)
        lang_code = LANG_MAP[lang]
        
        hyp = json.load(open(hyp_path))
        hyp_keys = set()
        for x in hyp:
            a = norm(x.get("audio_name") or x.get("audio_path") or "")
            s = round(float(x.get("start",x.get("start_time",0))),2)
            e = round(float(x.get("end",x.get("end_time",0))),2)
            hyp_keys.add((a,s,e))
        
        # Find missing
        missing = []
        for rf in sorted(os.listdir(ref_dir)):
            if not rf.endswith('.json'): continue
            d = json.load(open(os.path.join(ref_dir, rf)))
            aname = d.get("audio_name","")
            for seg in d.get("segments",[]):
                if seg.get("status") == "invalid": continue
                key = (norm(aname), round(float(seg["start"]),2), round(float(seg["end"]),2))
                if key not in hyp_keys:
                    audio_path = find_audio(aname, lang)
                    if audio_path:
                        missing.append((aname, float(seg["start"]), float(seg["end"]), audio_path))
        
        if not missing:
            print(f"{lang}: nothing to do")
            continue
        
        print(f"{lang}: {len(missing)} missing, transcribing...", flush=True)
        added = 0
        errors = 0
        
        for aname, start, end, audio_path in missing:
            try:
                text = transcribe(client, audio_path, start, end, lang_code)
                hyp.append({
                    "audio_name": aname,
                    "text": text,
                    "language": lang,
                    "model": "gpt4o-transcribe",
                    "start_time": start,
                    "end_time": end,
                })
                added += 1
                if added % 20 == 0:
                    with open(hyp_path, "w", encoding="utf-8") as f:
                        json.dump(hyp, f, ensure_ascii=False, indent=2)
                    print(f"  {lang}: {added}/{len(missing)} done", flush=True)
            except Exception as e:
                errors += 1
                err = str(e)
                if "429" in err or "quota" in err.lower():
                    print(f"  Rate limited, waiting 30s...", flush=True)
                    time.sleep(30)
                elif errors > 10:
                    print(f"  Too many errors, stopping {lang}", flush=True)
                    break
                else:
                    print(f"  Error: {err[:80]}", flush=True)
            time.sleep(0.5)
        
        with open(hyp_path, "w", encoding="utf-8") as f:
            json.dump(hyp, f, ensure_ascii=False, indent=2)
        print(f"{lang}: done +{added}, errors={errors}, total={len(hyp)}", flush=True)

if __name__ == "__main__":
    main()
