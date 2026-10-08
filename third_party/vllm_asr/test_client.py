"""HTTP contract and portability tests; no model weights or GPU required."""

from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import wave

from export import export


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "dataset" / "GROUP" / "input_prepare.json"
        self.manifest.parent.mkdir(parents=True)
        with wave.open(str(self.manifest.parent / "clip.wav"), "wb") as audio:
            audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\0\0" * 1600)
        self.row = {"segment_key": "example|0|100", "audio_path": "clip.wav",
                    "language": "EN", "ref_text": "REFERENCE_DO_NOT_TRANSMIT",
                    "hyp_text": "PREVIOUS_HYP_DO_NOT_TRANSMIT",
                    "meta": {"ref_audio_name": "example", "start_time": 0.0, "end_time": 0.1}}
        self.manifest.write_text(json.dumps([self.row]))
        self.responses = ["recognized speech"]
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                message = BytesParser(policy=default).parsebytes(
                    f"Content-Type: {self.headers['Content-Type']}\r\n\r\n".encode() + body)
                fields = {part.get_param("name", header="content-disposition"):
                          part.get_payload(decode=True) for part in message.iter_parts()}
                owner.requests.append((self.path, fields, body))
                result = owner.responses.pop(0) if len(owner.responses) > 1 else owner.responses[0]
                status = 500 if result is None else 200
                payload = json.dumps({"text": result}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/v1"

    def run_client(self, model="Qwen3-ASR-1.7B", extra=(), output="out", expected=0):
        script = Path(__file__).resolve().parents[1] / model / "infer.py"
        if model == "Fun-ASR-Nano":
            script = script.parent / "vllm" / "infer.py"
        cmd = [sys.executable, str(script), "--input-json", "dataset/GROUP/input_prepare.json",
               "--output-root", output, "--base-url", self.endpoint, "--workers", "2", *extra]
        result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        path = self.root / output / "output_raw.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_all_profiles_send_audio_only_and_preserve_metadata(self):
        for model in ("Qwen3-ASR-1.7B", "whisper-large-v3", "Fun-ASR-Nano"):
            with self.subTest(model=model):
                records = self.run_client(model, output=model)
                path, fields, body = self.requests[-1]
                self.assertEqual(path, "/v1/audio/transcriptions")
                expected = {"file", "model", "language", "temperature", "response_format"}
                if model == "Qwen3-ASR-1.7B":
                    expected.add("max_completion_tokens")
                self.assertEqual(set(fields), expected)
                self.assertEqual(fields["language"], b"en")
                self.assertNotIn(self.row["ref_text"].encode(), body)
                self.assertNotIn(self.row["hyp_text"].encode(), body)
                self.assertEqual(records[0]["audio_path"], "clip.wav")
                self.assertEqual(records[0]["meta"], self.row["meta"])

    def test_empty_retry_then_success_and_export(self):
        self.responses = ["language English<asr_text>", "language English<asr_text>hello"]
        record = self.run_client(extra=["--empty-retries", "10"])[0]
        self.assertEqual(record["hyp_text"], "hello")
        self.assertEqual(len(record["inference"]["attempts"]), 2)
        export(self.manifest, self.root / "out/output_raw.jsonl", self.root / "export")
        self.assertEqual(json.loads((self.root / "export/hyp.json").read_text()),
                         [{"audio_name": "example", "start": 0.0, "end": 0.1, "text": "hello"}])

    def test_persistent_empty_is_empty_string(self):
        self.responses = [" "]
        record = self.run_client(extra=["--empty-retries", "10"])[0]
        self.assertEqual(record["hyp_text"], "")
        self.assertEqual(record["status"], "done")
        self.assertEqual(len(self.requests), 11)

    def test_http_error_requires_explicit_retry_on_resume(self):
        self.responses = [None]
        self.run_client(expected=1)
        self.responses = ["recovered"]
        self.run_client(extra=["--resume"], expected=1)
        self.assertEqual(len(self.requests), 1)
        records = self.run_client(extra=["--resume", "--retry-errors"])
        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1]["hyp_text"], "recovered")

    def test_resume_rejects_changed_settings_or_manifest(self):
        self.run_client()
        self.run_client(extra=["--resume"])
        self.assertEqual(len(self.requests), 1)
        self.run_client(extra=["--resume", "--temperature", "0.2"], expected=1)
        self.row["ref_text"] = "changed"
        self.manifest.write_text(json.dumps([self.row]))
        self.run_client(extra=["--resume"], expected=1)
        self.assertEqual(len(self.requests), 1)

    def test_failed_retry_preserves_successful_empty(self):
        self.responses = ["", None]
        record = self.run_client(extra=["--empty-retries", "1"])[0]
        self.assertEqual(record["status"], "done")
        self.assertEqual(record["hyp_text"], "")

    def test_unsupported_funasr_language_sends_no_request(self):
        self.run_client("Fun-ASR-Nano", extra=["--language", "ko"], expected=1)
        self.assertEqual(self.requests, [])

    def test_export_rejects_incomplete_or_failed_runs(self):
        self.responses = [None]
        self.run_client(expected=1)
        with self.assertRaises(ValueError):
            export(self.manifest, self.root / "out/output_raw.jsonl", self.root / "export")
        (self.root / "out/output_raw.jsonl").write_text("")
        with self.assertRaises(ValueError):
            export(self.manifest, self.root / "out/output_raw.jsonl", self.root / "export")


if __name__ == "__main__":
    unittest.main()
