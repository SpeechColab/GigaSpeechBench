"""Test public dataset layout, language routing, clipping and staging export."""

import io
import argparse
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import numpy as np
import soundfile as sf

from client import language_code
from prepare import prepare_group
from run_benchmark import export_module, profile_for, setup_python


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source/Low-Resource-Languages/data/KOR"
        self.source.mkdir(parents=True)
        self.metadata = {"audios": [{"aid": "KOR#example", "segments": [
            {"sid": "KOR#example#0.1#0.3", "begin_time": "0.1", "end_time": "0.3",
             "text": "reference", "entities": ["entity"]},
            {"sid": "invalid", "begin_time": "0.0", "end_time": "0.1", "text": "skip", "status": "invalid"}
        ]}]}
        (self.source / "metadata.json").write_text(json.dumps(self.metadata))
        audio = io.BytesIO()
        sf.write(audio, np.ones((8000, 2)) * 0.25, 8000, format="WAV")
        self.audio = audio.getvalue()

    def archive(self):
        with tarfile.open(self.source / "audio.tar.gz", "w:gz") as tar:
            member = tarfile.TarInfo("audio/KOR#example.wav")
            member.size = len(self.audio)
            tar.addfile(member, io.BytesIO(self.audio))

    def test_archive_crop_resample_and_resume(self):
        self.archive()
        manifest = prepare_group(self.source, self.root / "prepared/KOR", "KOR")
        rows = json.loads(manifest.read_text())
        self.assertEqual(len(rows), 1)
        info = sf.info(manifest.parent / rows[0]["audio_path"])
        self.assertEqual((info.samplerate, info.channels, info.frames), (16000, 1, 3200))
        self.assertEqual(rows[0]["meta"]["source_segment"]["entities"], ["entity"])
        self.assertFalse(Path(rows[0]["audio_path"]).is_absolute())
        self.assertEqual(prepare_group(self.source, manifest.parent, "KOR"), manifest)
        with self.assertRaises(ValueError):
            prepare_group(self.source, manifest.parent, "KOR", 1)

    def test_extracted_layout(self):
        (self.source / "audio").mkdir()
        (self.source / "audio/KOR#example.wav").write_bytes(self.audio)
        manifest = prepare_group(self.source, self.root / "prepared/KOR", "KOR")
        self.assertEqual(len(json.loads(manifest.read_text())), 1)

    def test_missing_audio_fails_without_completion_marker(self):
        with self.assertRaises(FileNotFoundError):
            prepare_group(self.source, self.root / "prepared/KOR", "KOR")
        self.assertFalse((self.root / "prepared/KOR/prepare_spec.json").exists())

    def test_base_mlt_routing_and_arabic_country_codes(self):
        self.assertEqual(profile_for("funasr", "Low-Resource-Languages"), "funasr-mlt")
        for module in ("Vertical-Domain", "CH-EN-Dialects", "Older-Children"):
            self.assertEqual(profile_for("funasr", module), "funasr")
        for group in ("ARE", "DZA", "EGY", "IRQ", "MAR", "SAU", "SYR"):
            self.assertEqual(language_code(group, "funasr-mlt"), "ar")
        self.assertEqual(language_code("PHL", "qwen"), "tl")
        self.assertEqual(language_code("JPN-EN", "funasr"), "en")

    def test_python_override_preserves_venv_symlink(self):
        target = self.root / "system-python"
        target.touch()
        link = self.root / "venv-python"
        link.symlink_to(target)
        self.assertEqual(setup_python("qwen", argparse.Namespace(python_bin=link)), link)

    def test_staging_export_keeps_entities_and_empty_text(self):
        self.archive()
        manifest = prepare_group(self.source, self.root / "prepared/KOR", "KOR")
        row = json.loads(manifest.read_text())[0]
        row.update(status="done", hyp_text="")
        raw = self.root / "raw/KOR"
        raw.mkdir(parents=True)
        (raw / "output_raw.jsonl").write_text(json.dumps(row) + "\n")
        export_module(manifest.parent.parent, raw.parent, self.root / "work", "Low-Resource-Languages", "MLT")
        staging = self.root / "work/staging/Low-Resource-Languages"
        result = json.loads((staging / "results/MLT.json").read_text())
        self.assertEqual(result["audios"][0]["segments"][0]["text"], "")
        source = json.loads((staging / "data/KOR/metadata.json").read_text())
        self.assertEqual(source["audios"][0]["segments"][0]["entities"], ["entity"])


if __name__ == "__main__":
    unittest.main()
