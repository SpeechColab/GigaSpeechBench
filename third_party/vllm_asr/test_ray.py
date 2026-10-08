"""Validate the pinned FunASR call contract without importing GPU libraries."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf


class RayContractTests(unittest.TestCase):
    def test_tensor_input_and_single_generation_limit(self):
        path = Path(__file__).resolve().parents[1] / "Fun-ASR-Nano/ray/infer.py"
        spec = importlib.util.spec_from_file_location("ray_infer_contract", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tensor = object()
        calls = []

        class Model:
            def generate(self, **kwargs):
                calls.append(kwargs)
                return [{"text": "" if len(calls) == 1 else "recognized"}]

        worker = module.Worker.__new__(module.Worker)
        worker.model = Model()
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "clip.wav"
            sf.write(audio, np.zeros(1600, dtype="float32"), 16000)
            with patch.dict(sys.modules, {"torch": types.SimpleNamespace(from_numpy=lambda _: tensor)}):
                result = worker.transcribe(str(audio), "ko", 10)
        self.assertEqual(result["hyp_text"], "recognized")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["input"], [tensor])
        self.assertEqual(calls[0]["max_length"], 512)
        self.assertEqual(calls[0]["llm_kwargs"], {"do_sample": False})
        self.assertEqual(calls[0]["hotwords"], [])
        self.assertNotIn("ref_text", calls[0])


if __name__ == "__main__":
    unittest.main()
