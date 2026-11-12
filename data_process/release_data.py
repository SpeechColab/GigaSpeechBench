"""Read audio annotations from a WebDataset release or legacy metadata."""

import json
import tarfile
from pathlib import Path


def iter_audio_records(group_dir):
    group_dir = Path(group_dir)
    metadata = group_dir / "metadata.json"
    if metadata.is_file():
        with metadata.open(encoding="utf-8") as stream:
            yield from json.load(stream)["audios"]
        return

    shards = sorted((group_dir / "test").glob("*.tar"))
    if not shards:
        raise FileNotFoundError(f"No WebDataset shards or metadata.json in {group_dir}")
    for shard in shards:
        # Seek past WAV members: evaluating saved predictions only needs JSON.
        with tarfile.open(shard, "r:") as archive:
            for member in archive:
                if member.isfile() and member.name.endswith(".json"):
                    with archive.extractfile(member) as stream:
                        yield json.load(stream)
