import contextlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_process.convert_staging import convert_staging
from data_process.release_data import iter_audio_records
from scripts import build_excel, merge_excel
from scripts.hotword_wer import load_ref


class ReleasePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = {
            "aid": "CHILD-CH#012345abcdef",
            "segments": [
                {"begin_time": "0.000", "end_time": "1.000", "text": "你好", "status": "valid"},
                {"begin_time": "1.000", "end_time": "2.000", "text": "排除", "status": "invalid"},
            ],
        }

    def make_release(self, name, webdataset):
        module = self.root / name
        group = module / "data" / "CHILD-CH"
        group.mkdir(parents=True)
        if webdataset:
            (group / "test").mkdir()
            with tarfile.open(group / "test" / "00000.tar", "w") as archive:
                for suffix, content in [("wav", b"original audio bytes"), ("json", json.dumps(self.audio).encode())]:
                    member = tarfile.TarInfo(f"{self.audio['aid']}.{suffix}")
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))
        else:
            (group / "metadata.json").write_text(json.dumps({"audios": [self.audio]}))
        (module / "results").mkdir()
        prediction = {"audios": [{"aid": self.audio["aid"], "segments": [
            {"begin_time": "0.000", "end_time": "1.000", "text": ""},
        ]}]}
        (module / "results" / "MyModel.json").write_text(json.dumps(prediction))
        return module

    def convert(self, source, output, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            convert_staging(source, "Older-Children", output, **kwargs)

    def test_webdataset_and_metadata_produce_identical_evaluation_input(self):
        old = self.make_release("old", False)
        new = self.make_release("new", True)
        self.assertEqual(list(iter_audio_records(old / "data/CHILD-CH")),
                         list(iter_audio_records(new / "data/CHILD-CH")))
        for source, output in [(old, self.root / "old_out"), (new, self.root / "new_out")]:
            self.convert(source, output)
        for relative in ["ref/CHILD-CH.json", "hyp/CHILD-CH/CHILD-CH_MyModel.json"]:
            self.assertEqual((self.root / "old_out/data/text/Older-Children" / relative).read_bytes(),
                             (self.root / "new_out/data/text/Older-Children" / relative).read_bytes())
        refs = json.loads((self.root / "new_out/data/text/Older-Children/ref/CHILD-CH.json").read_text())
        self.assertEqual([s["text"] for s in refs], ["你好"])
        hyps = json.loads((self.root / "new_out/data/text/Older-Children/hyp/CHILD-CH/CHILD-CH_MyModel.json").read_text())
        self.assertEqual(hyps[0]["text"], "")

    def test_overwrite_and_skip_reference(self):
        source = self.make_release("old", False)
        output = self.root / "out"
        self.convert(source, output)
        ref = output / "data/text/Older-Children/ref/CHILD-CH.json"
        before = ref.read_bytes()
        self.audio["segments"][0]["text"] = "更新"
        (source / "data/CHILD-CH/metadata.json").write_text(json.dumps({"audios": [self.audio]}))
        self.convert(source, output, skip_existing=True)
        self.assertEqual(ref.read_bytes(), before)
        self.convert(source, output, skip_existing=False, skip_ref=True)
        self.assertEqual(ref.read_bytes(), before)
        self.convert(source, output, skip_existing=False)
        self.assertEqual(json.loads(ref.read_text())[0]["text"], "更新")

    def test_external_submission_does_not_modify_release(self):
        source = self.make_release("new", True)
        submission = source / "results/MyModel.json"
        before = submission.read_bytes()
        self.convert(source, self.root / "out", skip_ref=True, hyp_file=submission)
        self.assertEqual(submission.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in (source / "results").iterdir()), ["MyModel.json"])

    def test_hotword_annotations_survive_webdataset_loading(self):
        self.audio["segments"][0]["entities"] = [{"text": "你好"}]
        old = self.make_release("old", False)
        new = self.make_release("new", True)
        old_ref = load_ref(str(old / "data"), "CHILD-CH")
        new_ref = load_ref(str(new / "data"), "CHILD-CH")
        self.assertEqual(old_ref, new_ref)
        output = self.root / "converted"
        self.convert(new, output)
        aligned = load_ref(str(new / "data"), "CHILD-CH",
                           str(output / "data/text/Older-Children/ref"))
        self.assertEqual(len(aligned), 1)
        self.assertEqual(next(iter(aligned.values()))["entities"], [{"text": "你好"}])

    def test_excel_keeps_both_new_models_distinct(self):
        for name in ["QWEN-AUDIO-3.1-ASR-FLASH", "FUN-ASR-NANO-2512"]:
            folder = self.root / "scores/CHILD-CH" / name
            folder.mkdir(parents=True)
            (folder / "errs-test.txt").write_text("%WER = 12.50\n")
            (folder / "segment_check.txt").write_text("ref_segments=1\nhyp_segments=1\nmatched_segments=1\n")
        table = merge_excel.scan_module(str(self.root / "scores"), ["CHILD-CH"])
        _, active = merge_excel.prune_empty(table, ["CHILD-CH"])
        self.assertEqual(set(active), {"Qwen Audio 3.1 ASR Flash", "Fun-ASR-Nano-2512"})
        df = build_excel.scan_results(str(self.root / "scores"), ["CHILD-CH"])
        self.assertEqual(df.loc["Qwen Audio 3.1 ASR Flash", "CHILD-CH"], 12.5)
        self.assertEqual(df.loc["Fun-ASR-Nano-2512", "CHILD-CH"], 12.5)
        self.assertEqual(df.loc["FunASR-MLT-Nano", "CHILD-CH"], "-")

    def test_cli_recomputes_predictions_and_preserves_prepared_references(self):
        source = self.make_release("release", True)
        prediction = source / "results/Qwen-Audio-3.1-ASR-Flash.json"
        (source / "results/MyModel.json").rename(prediction)
        output = self.root / "cli"
        env = dict(os.environ, STAGING_ROOT=str(source), OUT_ROOT=str(output),
                   PYTHON_BIN=sys.executable, WORKERS="1", PYTHONDONTWRITEBYTECODE="1")
        command = ["bash", str(Path(__file__).resolve().parents[1] / "run_ASR.sh"), "Older-Children", "0"]
        first = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        scores = output / "data/results_Older-Children_mindur/CHILD-CH/QWEN-AUDIO-3.1-ASR-FLASH"
        error_file = scores / "errs-CHILD-CH-QWEN-AUDIO-3.1-ASR-FLASH.txt"
        self.assertEqual(error_file.read_text().splitlines()[0], "%WER = 100.00")
        ref = output / "data/text_normalized/Older-Children/ref/CHILD-CH.json"
        ref_mtime = ref.stat().st_mtime_ns
        stale = scores / "stale_marker"
        stale.touch()
        data = json.loads(prediction.read_text())
        data["audios"][0]["segments"][0]["text"] = "你好"
        prediction.write_text(json.dumps(data))
        second = subprocess.run(command + ["1"], env=env, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(error_file.read_text().splitlines()[0], "%WER = 0.00")
        self.assertEqual(ref.stat().st_mtime_ns, ref_mtime)
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
