"""Content-addressed OSS uploads and independently refreshed public GET URLs."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import oss2


class Storage:
    def __init__(self) -> None:
        region = os.environ['OSS_REGION']
        public = f'https://oss-{region}.aliyuncs.com'
        endpoint = os.getenv('OSS_ENDPOINT', public)
        token = os.getenv('OSS_SESSION_TOKEN')
        if token:
            auth = oss2.StsAuth(os.environ['OSS_ACCESS_KEY_ID'], os.environ['OSS_ACCESS_KEY_SECRET'], token)
        else:
            auth = oss2.AuthV4(os.environ['OSS_ACCESS_KEY_ID'], os.environ['OSS_ACCESS_KEY_SECRET'])
        bucket = os.environ['OSS_BUCKET_NAME']
        self.upload_bucket = oss2.Bucket(auth, endpoint, bucket, region=region, connect_timeout=30)
        self.public_bucket = oss2.Bucket(auth, public, bucket, region=region, connect_timeout=30)

    def upload(self, row: dict) -> None:
        path = Path(row['audio_path'])
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != row['sha256']:
            raise ValueError('Audio changed since manifest creation')
        try:
            try:
                head = self.upload_bucket.head_object(row['oss_key'])
            except oss2.exceptions.NoSuchKey:
                try:
                    self.upload_bucket.put_object(row['oss_key'], content,
                        headers={'x-oss-forbid-overwrite': 'true', 'Content-Type': 'audio/wav'})
                except oss2.exceptions.ServerError as exc:
                    if exc.code != 'FileAlreadyExists':
                        raise
                head = self.upload_bucket.head_object(row['oss_key'])
            if head.content_length != len(content) or head.etag.lower() != hashlib.md5(content).hexdigest():
                raise ValueError('Existing OSS object content does not match the local clip')
        except oss2.exceptions.OssError as exc:
            raise RuntimeError(f'OSS upload/check failed: {type(exc).__name__}, HTTP {exc.status}') from None

    def sign(self, row: dict) -> str:
        return self.public_bucket.sign_url('GET', row['oss_key'], 86400)
