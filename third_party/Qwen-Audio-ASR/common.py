"""Small serialization helpers shared only within this model directory."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

API_BASE = os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/api/v1').rstrip('/')


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'https?://[^\s"<>]+', '<URL_REDACTED>', value)
        for name in ('DASHSCOPE_API_KEY', 'OSS_ACCESS_KEY_ID', 'OSS_ACCESS_KEY_SECRET', 'OSS_SESSION_TOKEN'):
            secret = os.getenv(name)
            if secret:
                value = value.replace(secret, '<REDACTED>')
    return value


def extract(value: dict) -> str:
    output = value.get('output', {})
    if isinstance(output.get('text'), str):
        return output['text'].strip()
    nested = output.get('output', {})
    if isinstance(nested.get('text'), str):
        return nested['text'].strip()
    raise ValueError('Missing documented full-transcript text field')
