#!/usr/bin/env python3
"""
Run qwen3.5-omni-flash ASR on all fleurs languages.
Saves results as hyp files to BenchData.
"""
import json, os, time, subprocess, tempfile
from collections import defaultdict
import dashscope

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
API_KEY = os.getenv("DASHSCOPE_API_KEY")
MODEL = "qwen3.5-omni-flash"
OUTPUT_MODEL = "qwen3.5-omni-flash"  # model field in hyp

BASE = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark"
TOL = 0.1

LANG_MAP = {
    "EGY": "ar", "IDN": "id", "JPN": "ja", "KOR": "ko",
    "MYS": "ms", "PHL": "fil", "THA": "th", "VNM": "vi",
    # common-voice
    "AR": "ar",
    # Low-Resource-Languages
    "ARE": "ar", "DZA": "ar", "IRQ": "ar", "MAR": "ar", "SAU": "ar", "SYR": "ar",
}

MODULES = {
    "fleurs": {
        "ref_root": os.path.join(BASE, "fleurs/text/ref"),
        "hyp_dir": os.path.join(BASE, "fleurs/text/hyp"),
        "audio_roots": [
            os.path.join(BASE, "fleurs/audio"),
            os.path.join(BASE, "fleurs/audio/testbatch"),
            os.path.join(BASE, "fleurs/audio/batch_1"),
            os.path.join(BASE, "fleurs/audio/batch_2"),
        ],
    },
    "common-voice": {
        "ref_root": os.path.join(BASE, "common-voice/text/ref"),
        "hyp_dir": os.path.join(BASE, "common-voice/text/hyp"),
        "audio_roots": [
            os.path.join(BASE, "common-voice/audio"),
            os.path.join(BASE, "common-voice/audio/testbatch"),
            os.path.join(BASE, "common-voice/audio/batch_1"),
            os.path.join(BASE, "common-voice/audio/batch_2"),
        ],
    },
    "Low-Resource-Languages": {
        "ref_root": os.path.join(BASE, "Low-Resource-Languages/text/ref"),
        "hyp_dir": os.path.join(BASE, "Low-Resource-Languages/text/hyp"),
        "audio_roots": [
            os.path.join(BASE, "Low-Resource-Languages/audio"),
            os.path.join(BASE, "Low-Resource-Languages/audio/testbatch"),
            os.path.join(BASE, "Low-Resource-Languages/audio/batch_1"),
            os.path.join(BASE, "Low-Resource-Languages/audio/batch_2"),
            "/home/v-yujietu/BenchData/SYR_audio_tmp",
        ],
    },
}

def norm(a):
    b = os.path.basename(str(a).replace("\\","/"))
    while True:
        ch=False
        for e in [".wav",".mp3",".mp4",".webm"]:
            if b.lower().endswith(e): b=b[:-len(e)]; ch=True
        if not ch: break
    if b.endswith("#raw"): b=b[:-4]
    return b

def find_audio(aname, lang, audio_roots):
    # Try exact name first (may already have extension)
    for root in audio_roots:
        for candidate in [f"{lang}/{aname}", f"{aname}",
                          f"{lang}/{aname}.wav", f"{lang}/{aname}.mp3",
                          f"{aname}.wav", f"{aname}.mp3",
                          f"{lang}/{aname.replace('#','_')}.wav",
                          f"{lang}/{aname.replace('#','_')}.mp3",
                          f"{aname.replace('#','_')}.wav"]:
            p = os.path.join(root, candidate)
            if os.path.isfile(p): return p
    return None

def cut_wav(src, start, end):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    subprocess.run(["ffmpeg","-y","-i",src,"-ss",str(start),"-to",str(end),
                     "-ac","1","-ar","16000",tmp.name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tmp.name

def transcribe(wav_path, lang_code):
    response = dashscope.MultiModalConversation.call(
        api_key=API_KEY,
        model=MODEL,
        messages=[{"role":"user","content":[
            {"audio": wav_path},
            {"text": "Transcribe this audio accurately."}
        ]}],
        result_format="message",
    )
    if response.status_code == 200:
        choices = response.output.get("choices",[])
        if choices:
            content = choices[0].get("message",{}).get("content",[])
            if content:
                return content[0].get("text",""), response.usage
    return "", response.usage if hasattr(response,'usage') else {}

def main():
    total_cost_audio = 0
    total_cost_text_in = 0
    total_cost_text_out = 0
    
    for mod_name, mod_cfg in MODULES.items():
        ref_root = mod_cfg["ref_root"]
        hyp_dir = mod_cfg["hyp_dir"]
        audio_roots = mod_cfg["audio_roots"]
        
        langs = sorted([d for d in os.listdir(ref_root) if os.path.isdir(os.path.join(ref_root, d))])
        
        for lang in langs:
            hyp_path = os.path.join(hyp_dir, f"{lang}_{OUTPUT_MODEL}.json")
            ref_dir = os.path.join(ref_root, lang)
            
            # Load existing hyp for resume
            hyp = []
            hyp_keys = set()
            if os.path.exists(hyp_path):
                hyp = json.load(open(hyp_path))
                for x in hyp:
                    a = norm(x.get("audio_name") or x.get("audio_path",""))
                    s = round(float(x.get("start",x.get("start_time",0))),2)
                    e = round(float(x.get("end",x.get("end_time",0))),2)
                    hyp_keys.add((a,s,e))
            
            # Collect missing segments
            missing = []
            for rf in sorted(os.listdir(ref_dir)):
                if not rf.endswith('.json'): continue
                d = json.load(open(os.path.join(ref_dir, rf)))
                aname = d.get("audio_name","")
                audio_path = find_audio(aname, lang, audio_roots)
                if not audio_path: continue
                for seg in d.get("segments",[]):
                    if seg.get("status") == "invalid": continue
                    start, end = float(seg["start"]), float(seg["end"])
                    key = (norm(aname), round(start,2), round(end,2))
                    if key not in hyp_keys:
                        missing.append((aname, start, end, audio_path))
            
            if not missing:
                print(f"{mod_name}/{lang}: already complete ({len(hyp)} segs)", flush=True)
                continue
            
            print(f"{mod_name}/{lang}: {len(missing)} missing, transcribing...", flush=True)
            added = 0
            errors = 0
            lang_audio_tokens = 0
            lang_text_in = 0
            lang_text_out = 0
            
            for aname, start, end, audio_path in missing:
                tmp = cut_wav(audio_path, start, end)
                try:
                    text, usage = transcribe(tmp, LANG_MAP.get(lang, "auto"))
                    hyp.append({
                        "audio_name": aname,
                        "text": text,
                        "language": lang,
                        "model": OUTPUT_MODEL,
                        "start_time": start,
                        "end_time": end,
                    })
                    added += 1
                    
                    # Track token usage
                    if usage:
                        details = usage.get("input_tokens_details", {})
                        lang_audio_tokens += details.get("audio_tokens", 0)
                        lang_text_in += details.get("text_tokens", 0)
                        lang_text_out += usage.get("output_tokens", 0)
                    
                    if added % 50 == 0:
                        with open(hyp_path, "w", encoding="utf-8") as f:
                            json.dump(hyp, f, ensure_ascii=False, indent=2)
                        print(f"  [{added}/{len(missing)}] saved", flush=True)
                except Exception as e:
                    errors += 1
                    err = str(e)
                    if "429" in err or "Throttling" in err:
                        print(f"  Rate limited, wait 10s", flush=True)
                        time.sleep(10)
                    else:
                        print(f"  Error: {err[:80]}", flush=True)
                finally:
                    os.unlink(tmp)
                time.sleep(0.3)
            
            # Final save
            with open(hyp_path, "w", encoding="utf-8") as f:
                json.dump(hyp, f, ensure_ascii=False, indent=2)
            
            # Cost calculation
            cost_audio = lang_audio_tokens / 1e6 * 3  # $3/M
            cost_tin = lang_text_in / 1e6 * 0.4  # $0.4/M
            cost_tout = lang_text_out / 1e6 * 2.2  # $2.2/M
            total_cost_audio += cost_audio
            total_cost_text_in += cost_tin
            total_cost_text_out += cost_tout
            
            print(f"  {lang}: +{added}, errors={errors}, total={len(hyp)}", flush=True)
            print(f"  tokens: audio={lang_audio_tokens}, text_in={lang_text_in}, text_out={lang_text_out}", flush=True)
            print(f"  cost: ${cost_audio+cost_tin+cost_tout:.4f}", flush=True)
    
    total = total_cost_audio + total_cost_text_in + total_cost_text_out
    print(f"\n=== TOTAL COST ===")
    print(f"  Audio input: ${total_cost_audio:.4f}")
    print(f"  Text input:  ${total_cost_text_in:.4f}")
    print(f"  Text output: ${total_cost_text_out:.4f}")
    print(f"  Total:       ${total:.4f}")

if __name__ == "__main__":
    main()
