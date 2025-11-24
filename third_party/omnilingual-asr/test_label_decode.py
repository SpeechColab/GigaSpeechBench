import json
import os, sys
import argparse
from tqdm import tqdm
from pathlib import Path
from omniasr import batch_transcribe_audios


def get_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--label-dir", 
        type=str, 
        default='data/multilingual-asr-bench-label',
        help="Path to where labels located. Should include different language folders"
    )
    parser.add_argument(
        "--audio-dir", 
        type=str, 
        default='data/',
        help="Path to where audio files located. Should include different language folders"
    )
    parser.add_argument(
        '--batch-decode', 
        action='store_true', 
        help='If False, the decoding process will be for loop to avoid error'
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default='omniASR_CTC_3B',
        help="used for choosing the ASR model"
    )
    return parser


def extract_valid_segments(audio_dir, json_path, lang):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    audio_path = os.path.join(audio_dir, lang, f'{data["audio_name"]}.wav')
    result = [
        (audio_path, str(seg["start"]), str(seg["end"]))
        for seg in data["segments"]
        if seg.get("status") == "valid"
    ]

    return result


def main():
    parser = get_parser()
    args = parser.parse_args()

    languages = [
        "ARE", "DZA", "EGY", 
        "IDN", "IRQ", "JPN", "KOR", 
        "MAR", "PHL", "SAU", 
        "VNM", "THA", "MYS", 
    ]
    for lang in languages:
        print('Now processing: ', lang)
    
        label_dir = os.path.join(args.label_dir, lang)
        metainfo_output = os.path.join(label_dir, f'{lang}_segments')

        metainfo = []
        for json_file in Path(label_dir).rglob("*.json"):
            metainfo.extend(extract_valid_segments(args.audio_dir, json_file, lang))

        with open(metainfo_output, 'w') as out:
            for segment in tqdm(metainfo):
                out.write('\t'.join(segment)+'\n')

        batch_transcribe_audios(
            input_file=metainfo_output,
            model=args.model,
            language=lang,
            batch_decode=args.batch_decode,
            batch_size=4,
        )


if __name__ == "__main__":
    main()
