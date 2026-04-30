#!/usr/bin/env python3
"""Run qwen3-asr-flash on missing common-voice VNM segments."""
import json, os, time, subprocess, tempfile
from collections import defaultdict
import dashscope

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
API_KEY = "REDACTED_DASHSCOPE_KEY"

BASE = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark"
REF_DIR = os.path.join(BASE, "common-voice/text/ref/VNM")
HYP_PATH = os.path.join(BASE, "common-voice/text/hyp/VNM_qwen3-asr-flash.json")
AUDIO_ROOT = os.path.join(BASE, "common-voice/audio")
TOL = 0.1

def norm(a):
    b = os.path.basename(str(a).replace("\\","/"))
    while True:
        ch=False
        for e in [".wav",".mp3",".mp4",".webm"]:
            if b.lower().endswith(e): b=b[:-len(e)]; ch=True
        if not ch: break
    return b

def find_audio(aname):
    for root, dirs, files in os.walk(AUDIO_ROOT):
        if "VNM" not in root: continue
        for f in files:
            if norm(f) == norm(aname):
                return os.path.join(root, f)
    return None

def cut_wav(src, start, end):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    subprocess.run(["ffmpeg","-y","-i",src,"-ss",str(start),"-to",str(end),
                     "-ac","1","-ar","16000",tmp.name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tmp.name

def transcribe(wav_path):
    response = dashscope.MultiModalConversation.call(
        api_key=API_KEY,
        model="qwen3-asr-flash",
        messages=[{"role":"user","content":[{"audio": wav_path}]}],
        result_format="message",
        asr_options={"enable_itn": True, "language": "vi"},
    )
    if response.status_code == 200:
        choices = response.output.get("choices",[])
        if choices:
            content = choices[0].get("message",{}).get("content",[])
            if content:
                return content[0].get("text","")
    return ""

def main():
    hyp = json.load(open(HYP_PATH))
    hyp_keys = set()
    for x in hyp:
        a = norm(x.get("audio_name") or x.get("audio_path") or x.get("path",""))
        s = round(float(x.get("start",x.get("start_time",0))),2)
        e = round(float(x.get("end",x.get("end_time",0))),2)
        hyp_keys.add((a,s,e))

    missing = []
    for rf in sorted(os.listdir(REF_DIR)):
        if not rf.endswith('.json'): continue
        d = json.load(open(os.path.join(REF_DIR, rf)))
        aname = d.get("audio_name","")
        for seg in d.get("segments",[]):
            if seg.get("status") == "invalid": continue
            key = (norm(aname), round(float(seg["start"]),2), round(float(seg["end"]),2))
            if key not in hyp_keys:
                audio_path = find_audio(aname)
                if audio_path:
                    missing.append((aname, float(seg["start"]), float(seg["end"]), audio_path))

    print(f"Missing: {len(missing)} segments", flush=True)
    added = 0
    errors = 0

    for aname, start, end, audio_path in missing:
        tmp = cut_wav(audio_path, start, end)
        try:
            text = transcribe(tmp)
            hyp.append({
                "audio_name": aname,
                "text": text,
                "language": "VNM",
                "model": "qwen3-asr-flash",
                "start_time": start,
                "end_time": end,
            })
            added += 1
            if added % 20 == 0:
                with open(HYP_PATH,"w",encoding="utf-8") as f:
                    json.dump(hyp, f, ensure_ascii=False, indent=2)
                print(f"  [{added}/{len(missing)}] saved", flush=True)
        except Exception as e:
            errors += 1
            print(f"  Error: {str(e)[:80]}", flush=True)
            time.sleep(2)
        finally:
            os.unlink(tmp)
        time.sleep(0.3)

    with open(HYP_PATH,"w",encoding="utf-8") as f:
        json.dump(hyp, f, ensure_ascii=False, indent=2)
    print(f"Done: +{added}, errors={errors}, total={len(hyp)}")

if __name__ == "__main__":
    main()
