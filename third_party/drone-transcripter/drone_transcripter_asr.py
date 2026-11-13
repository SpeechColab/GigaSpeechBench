#!/usr/bin/env python3
"""Transcribe a GigaSpeechBench test set with Drone Transcripter 4 or 4 Mini.

Writes the result JSON the toolkit scores (audios[].segments[].{sid,begin_time,end_time,text}).

Segment-level decoding: every reference segment (begin/end from metadata.json) is cut from its
recording, resampled to 16 kHz mono and transcribed on its own, 64 segments per batch, greedy.
Raw model text is kept; the toolkit's text_norm/<LANG>.py normalises ref and hyp alike.

    python drone_transcripter_asr.py --model v4   --audio_root EGY/audio --metadata EGY/metadata.json \
        --output results/EGY_Drone-Transcripter-4.json
    python drone_transcripter_asr.py --model mini --audio_root EGY/audio --metadata EGY/metadata.json \
        --output results/EGY_Drone-Transcripter-4-Mini.json
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import time

SR = 16000
MIN_SAMPLES = SR // 10  # clips shorter than 0.1 s are replaced by 0.1 s of silence
MAX_SAMPLES = 30 * SR  # Whisper input window

HF_REPOS = {
    "v4": ("AbdelrhmanX2/drone-transcripter-4", "drone-transcripter-v4"),
    "mini": ("AbdelrhmanX2/drone-transcripter-4-mini", "drone-transcripter-4-mini.nemo"),
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", choices=["v4", "mini"], required=True,
                   help="v4: 809M Whisper large-v3-turbo fine-tune; mini: 115M FastConformer hybrid RNN-T/CTC")
    p.add_argument("--audio_root", required=True, help="directory holding the recordings (searched recursively)")
    p.add_argument("--metadata", required=True, help="GigaSpeechBench metadata.json of the test set")
    p.add_argument("--output", required=True, help="result JSON to write")
    p.add_argument("--language", default=None,
                   help="language code written to the output (default: from metadata, else EGY)")
    p.add_argument("--model_path", default=None,
                   help="local checkpoint (v4: HF model dir, mini: .nemo file); default: download from Hugging Face")
    p.add_argument("--device", default=None, help="torch device, e.g. cuda, cuda:1, cpu (default: cuda if available)")
    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--decoder", choices=["rnnt", "ctc"], default="rnnt", help="mini only: decoding head")
    return p.parse_args()


def resolve_model_path(args):
    if args.model_path:
        return args.model_path
    from huggingface_hub import hf_hub_download, snapshot_download

    repo, sub = HF_REPOS[args.model]
    if args.model == "v4":
        return os.path.join(snapshot_download(repo, allow_patterns=[f"{sub}/*"]), sub)
    return hf_hub_download(repo, sub)


def find_audio(root, aid):
    for pattern in (aid.split("#")[-1], aid):
        hits = [p for p in glob.glob(os.path.join(glob.escape(root), "**", glob.escape(pattern) + "*"), recursive=True)
                if os.path.isfile(p)]
        if hits:
            return sorted(hits)[0]
    raise FileNotFoundError(f"no audio for {aid} under {root}")


def load_audio(path):
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def cut(wav, seg, max_samples=None):
    import numpy as np

    b, e = int(float(seg["begin_time"]) * SR), int(float(seg["end_time"]) * SR)
    if max_samples:
        e = min(e, b + max_samples)
    clip = wav[b:e]
    return clip if len(clip) >= MIN_SAMPLES else np.zeros(MIN_SAMPLES, np.float32)


def build_v4(path, device, batch_size):
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    proc = AutoProcessor.from_pretrained(path)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(path, torch_dtype=dtype).to(device).eval()

    def transcribe(wav, segs):
        texts = []
        for i in range(0, len(segs), batch_size):
            clips = [cut(wav, s, MAX_SAMPLES) for s in segs[i:i + batch_size]]
            feats = proc.feature_extractor(clips, sampling_rate=SR, return_tensors="pt").input_features
            with torch.no_grad():
                ids = model.generate(feats.to(device, dtype), language="ar", task="transcribe",
                                     num_beams=1, do_sample=False, max_new_tokens=200)
            texts += [" ".join(t.split()) for t in proc.batch_decode(ids, skip_special_tokens=True)]
        return texts

    return transcribe


def build_mini(path, device, batch_size, decoder):
    import contextlib

    import soundfile as sf
    import torch
    from nemo.collections.asr.models import ASRModel

    model = ASRModel.restore_from(path, map_location=device).eval()
    model.change_decoding_strategy(decoder_type=decoder)  # greedy is the model's default strategy
    autocast = (lambda: torch.autocast("cuda", dtype=torch.bfloat16)) if device.startswith("cuda") \
        else contextlib.nullcontext
    tmp = tempfile.mkdtemp()

    def texts_of(out):
        if isinstance(out, tuple):
            out = out[0]
        return [o if isinstance(o, str) else getattr(o, "text", "") or "" for o in out]

    def transcribe(wav, segs):
        paths = []
        for n, s in enumerate(segs):
            p = os.path.join(tmp, f"{n}.wav")
            sf.write(p, cut(wav, s), SR)
            paths.append(p)
        texts = []
        try:
            for i in range(0, len(paths), batch_size):
                with torch.no_grad(), autocast():
                    texts += texts_of(model.transcribe(paths[i:i + batch_size], batch_size=batch_size, verbose=False))
        finally:
            for p in paths:
                os.remove(p)
        return [t.strip() for t in texts]

    return transcribe


def main():
    args = parse_args()
    import torch

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    path = resolve_model_path(args)
    if args.model == "v4":
        transcribe = build_v4(path, device, args.batch_size)
    else:
        transcribe = build_mini(path, device, args.batch_size, args.decoder)

    with open(args.metadata, encoding="utf-8") as f:
        meta = json.load(f)
    result, t0, nseg = {"audios": []}, time.time(), 0
    for i, a in enumerate(meta["audios"], 1):
        segs = a["segments"]
        texts = transcribe(load_audio(find_audio(args.audio_root, a["aid"])), segs)
        result["audios"].append({
            "aid": a["aid"],
            "language": args.language or a.get("language") or a["aid"].split("#")[0] or "EGY",
            "segments": [{"sid": s["sid"], "begin_time": s["begin_time"], "end_time": s["end_time"], "text": t}
                         for s, t in zip(segs, texts)],
        })
        nseg += len(segs)
        print(f"[{i}/{len(meta['audios'])}] {a['aid']} {len(segs)} segs, {nseg} total, {time.time() - t0:.0f} s",
              file=sys.stderr, flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    print(f"wrote {len(result['audios'])} audios, {nseg} segments -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
