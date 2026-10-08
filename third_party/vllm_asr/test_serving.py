"""Check managed-server teardown without a GPU or model download."""

import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest


class ServingTests(unittest.TestCase):
    def test_interruption_stops_detached_server_during_startup(self):
        module_dir = Path(__file__).resolve().parent
        for stop_signal in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=stop_signal), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                (root / "serve.sh").write_text(
                    '#!/usr/bin/env bash\nset -euo pipefail\n'
                    'echo "$$" > "$GSB_TEST_PID"\nexec sleep 120\n')
                code = '''import signal, sys
from pathlib import Path
from types import SimpleNamespace
import run_benchmark as runner
runner.THIRD_PARTY = Path(sys.argv[1])
runner.FOLDERS = {"qwen": "."}
for sig in (signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, runner.interrupted)
args = SimpleNamespace(port=int(sys.argv[2]), gpus="0", model_path=None, startup_timeout=60)
with runner.serving("qwen", Path(sys.executable), args, runner.THIRD_PARTY / "server.log"):
    raise AssertionError("The fake server must never pass health")
'''
                env = dict(os.environ, PYTHONPATH=str(module_dir), GSB_TEST_PID=str(root / "pid"))
                process = subprocess.Popen([sys.executable, "-c", code, str(root), str(port)],
                                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                server_pid = None
                try:
                    deadline = time.monotonic() + 10
                    while not (root / "pid").exists():
                        if process.poll() is not None or time.monotonic() > deadline:
                            self.fail("Managed fake server failed to start")
                        time.sleep(0.02)
                    server_pid = int((root / "pid").read_text())
                    process.send_signal(stop_signal)
                    self.assertNotEqual(process.wait(timeout=10), 0)
                    with self.assertRaises(ProcessLookupError):
                        os.kill(server_pid, 0)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    if server_pid:
                        try:
                            os.killpg(server_pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass


if __name__ == "__main__":
    unittest.main()
