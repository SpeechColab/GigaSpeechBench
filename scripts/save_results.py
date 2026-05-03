#!/usr/bin/env python3
"""
Helper to save ASR transcription results in GigaSpeech-style JSON format.

Usage in third_party model scripts:

    from scripts.save_results import ResultWriter

    writer = ResultWriter()
    for audio_name, segments in my_results:
        for seg in segments:
            writer.add(audio_name, seg["begin_time"], seg["end_time"], seg["text"], lang="ARE")
    writer.save("results/my_model.json")

Or directly build from a list:

    save_results(segments, "results/my_model.json")

where each segment is:
    {"audio_name": "ARE#...", "begin_time": 0.0, "end_time": 5.0, "text": "...", "lang": "ARE"}
"""

import json
from collections import OrderedDict, defaultdict


class ResultWriter:
    """Incrementally build GigaSpeech-style results JSON."""

    def __init__(self):
        self._audios = defaultdict(list)  # aid -> [segments]
        self._counter = 0

    def add(self, audio_name: str, begin_time: float, end_time: float,
            text: str, lang: str = ""):
        """Add a single segment result."""
        self._counter += 1
        seg = OrderedDict()
        seg["sid"] = f"{audio_name}_{self._counter}"
        seg["begin_time"] = begin_time
        seg["end_time"] = end_time
        seg["text"] = text
        if lang:
            seg["lang"] = lang
        self._audios[audio_name].append(seg)

    def save(self, path: str):
        """Write all results to a GigaSpeech-style JSON file."""
        audios = []
        for aid in sorted(self._audios.keys()):
            segs = sorted(self._audios[aid], key=lambda s: s["begin_time"])
            entry = OrderedDict()
            entry["aid"] = aid
            entry["segments"] = segs
            audios.append(entry)

        with open(path, "w", encoding="utf-8") as f:
            json.dump({"audios": audios}, f, ensure_ascii=False, indent=2)
        total = sum(len(a["segments"]) for a in audios)
        print(f"Saved {total} segments ({len(audios)} audios) -> {path}")


def save_results(segments: list, path: str):
    """
    Save a flat list of segments to GigaSpeech-style JSON.

    Each segment must have: audio_name, begin_time, end_time, text, lang
    """
    writer = ResultWriter()
    for seg in segments:
        writer.add(
            audio_name=seg["audio_name"],
            begin_time=seg["begin_time"],
            end_time=seg["end_time"],
            text=seg["text"],
            lang=seg.get("lang", ""),
        )
    writer.save(path)
