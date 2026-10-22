"""Stable JSON hashing and atomic, concurrent-reader-safe output."""
import hashlib
import json
import os
from uuid import uuid4
from pathlib import Path


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.stem}-{uuid4().hex}.tmp"
    created = False
    try:
        # A unique path with exclusive creation fails immediately on denied writes.
        # NamedTemporaryFile may retry EACCES extensively on some Windows policies.
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            created = True
            stream.write(canonical_json(value))
        os.replace(temporary, path)
    finally:
        if created and temporary.exists():
            temporary.unlink()
