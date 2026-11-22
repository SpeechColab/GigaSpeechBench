import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

import numpy as np
import soundfile as sf

RUNNER = Path(__file__).resolve().parents[1] / "third_party" / "Qwen3-ASR-1.7B"
sys.path.insert(0, str(RUNNER))
from prepare import prepare_group


class QwenWebDatasetTest(unittest.TestCase):
    def test_shards_match_legacy_and_reuse_validated_cache(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            group = "PHL-EN"
            legacy = root / "legacy"
            web = root / "dataset" / "CH-EN-Dialects" / "data" / group
            (legacy / "audio").mkdir(parents=True)
            (web / "test").mkdir(parents=True)
            records = []
            for i in range(2):
                aid = f"{group}#{i}"
                rate = 8000
                data = np.sin(np.arange(rate * 2) * 0.1)
                wav = legacy / "audio" / (aid + ".wav")
                sf.write(wav, data, rate)
                rec = {
                    "aid": aid,
                    "language": group,
                    "segments": [
                        {"sid": aid + "#0.1#1.2", "begin_time": "0.1", "end_time": "1.2", "text": "test"},
                        {
                            "sid": aid + "#1.2#1.5",
                            "begin_time": "1.2",
                            "end_time": "1.5",
                            "text": "ignored",
                            "status": "invalid",
                        },
                    ],
                }
                records.append(rec)
                with tarfile.open(web / "test" / f"{i:05}.tar", "w") as tar:
                    tar.add(wav, arcname=wav.name)
                    content = json.dumps(rec).encode()
                    member = tarfile.TarInfo(aid + ".json")
                    member.size = len(content)
                    tar.addfile(member, io.BytesIO(content))
            (legacy / "metadata.json").write_text(json.dumps({"audios": records}))
            # A leftover extraction must not override the fingerprinted shard.
            (web / "audio").mkdir()
            (web / "audio" / f"{group}#0.wav").write_bytes(b"stale extraction")
            cli = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER / "run.py"),
                    "--subset",
                    "dialects",
                    "--groups",
                    group,
                    "--data-root",
                    str(root / "dataset"),
                    "--work-dir",
                    str(root / "cli"),
                    "--prepare-only",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("2 clips", cli.stdout)
            legacy_manifest = prepare_group(legacy, root / "a", group)
            web_dir = root / "cli" / "prepared" / "CH-EN-Dialects" / group
            web_manifest = web_dir / "input_prepare.json"
            self.assertEqual(legacy_manifest.read_bytes(), web_manifest.read_bytes())
            rows = json.loads(legacy_manifest.read_text())
            self.assertEqual(len(rows), 2)
            for row in rows:
                legacy_wav = legacy_manifest.parent / row["audio_path"]
                web_wav = web_manifest.parent / row["audio_path"]
                self.assertEqual(legacy_wav.read_bytes(), web_wav.read_bytes())
                self.assertEqual(sf.info(web_wav).samplerate, 16000)
                self.assertEqual(sf.info(web_wav).frames, 17600)
            self.assertEqual(prepare_group(web, web_dir, group), web_manifest)
            with (web / "test" / "00001.tar").open("ab") as f:
                f.write(bytes(512))
            with self.assertRaisesRegex(ValueError, "Preparation settings changed"):
                prepare_group(web, web_dir, group)


if __name__ == "__main__":
    unittest.main()
