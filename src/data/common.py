"""Cached HTTP acquisition, immutable raw artifacts and a shared source ledger."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx
import pandas as pd

from src.data.bootstrap import LOG_FIELDS
from src.utils.serialization import atomic_json, digest


class SourceError(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_url(url, secrets=()):
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host += ":" + str(parts.port)
    query = [(key, "REDACTED" if re.search(r"key|token|secret|signature|auth|credential", key, re.I) else value)
             for key, value in parse_qsl(parts.query, keep_blank_values=True)]
    path = re.sub(r"(/api/)[^/]+(/subgraphs/)", r"\1REDACTED\2", parts.path)
    result = urlunsplit((parts.scheme, host, path, urlencode(query), ""))
    for secret in secrets:
        if secret:
            result = result.replace(secret, "REDACTED")
    return result


def atomic_bytes(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ("." + path.name + "." + uuid4().hex + ".tmp")
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(content)
        temporary.replace(path)
    finally:
        if created and temporary.exists():
            temporary.unlink()


def record_count(payload):
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return len(payload["data"])
    if isinstance(payload, dict) and isinstance(payload.get("result"), list):
        return len(payload["result"])
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]
        if "attributes" in data and "ohlcv_list" in data["attributes"]:
            return len(data["attributes"]["ohlcv_list"])
        if len(data) == 1 and isinstance(next(iter(data.values())), list):
            return len(next(iter(data.values())))
    return 1


class Acquisition:
    def __init__(self, root, *, timeout=30, attempts=4, requests_per_second=2, transport=None, secrets=()):
        self.root = Path(root)
        self.root.joinpath("data/raw").mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "data/source_log.csv"
        self.secrets = tuple(value for value in secrets if value)
        self.attempts = attempts
        self.delay = 1 / requests_per_second
        self.last_request = 0.0
        self.client = httpx.Client(timeout=timeout, transport=transport, follow_redirects=True,
                                   headers={"User-Agent": "Uniswap-LP-Research/0.3 (public-data-research)", "Accept": "application/json"})
        self.known = set()
        if self.log_path.exists():
            with self.log_path.open(encoding="utf-8", newline="") as stream:
                self.known = {(row["file_path"], row["sha256"]) for row in csv.DictReader(stream)}
        self.artifacts = {}
        self.requests = 0
        self.cache_hits = 0
        self.source_last = {}
        self.source_delay = {"geckoterminal": 6.2, "coingecko": 6.2}

    def close(self):
        self.client.close()

    def log(self, source, endpoint, path, rows, *, start="", end="", kind="observed", downloaded_at=None):
        path = Path(path)
        relative = path.relative_to(self.root).as_posix()
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        entry = {"source": source, "endpoint": safe_url(endpoint, self.secrets), "downloaded_at_utc": downloaded_at or utc_now(),
                 "period_start": str(start), "period_end": str(end), "row_count": rows, "file_path": relative,
                 "sha256": sha, "data_kind": kind}
        if (relative, sha) not in self.known:
            needs_header = not self.log_path.exists() or self.log_path.stat().st_size == 0
            with self.log_path.open("a", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=LOG_FIELDS)
                if needs_header:
                    writer.writeheader()
                writer.writerow(entry)
            self.known.add((relative, sha))
        self.artifacts[relative] = entry
        return entry

    def request(self, source, method, url, *, params=None, body=None, headers=None, ttl=None, force=False, extension="json", start="", end=""):
        safe = safe_url(str(httpx.URL(url, params=params)), self.secrets)
        safe_body = json.dumps(body, sort_keys=True)
        for secret in self.secrets:
            safe_body = safe_body.replace(secret, "REDACTED")
        identity = {"source": source, "method": method, "url": safe, "body": json.loads(safe_body)}
        key = digest(identity)
        directory = self.root / "data/raw" / source / key
        metadata_path = directory / "request.json"
        if metadata_path.exists() and not force:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            raw = self.root / metadata["file_path"]
            fresh = ttl is None or time.time() - metadata["fetched_epoch"] < ttl
            if metadata["status"] >= 400:
                fresh = fresh and time.time() - metadata["fetched_epoch"] < 30
            if fresh and raw.exists() and hashlib.sha256(raw.read_bytes()).hexdigest() == metadata["sha256"]:
                self.cache_hits += 1
                if metadata["status"] >= 400:
                    raise SourceError(f"{source}: HTTP {metadata['status']} ({safe}); cached response")
                self.log(source, safe, raw, metadata["row_count"], start=start, end=end, downloaded_at=metadata["downloaded_at_utc"])
                return raw.read_bytes(), metadata
        final = None
        for attempt in range(self.attempts):
            pause = max(self.delay - (time.monotonic() - self.last_request),
                        self.source_delay.get(source, 0) - (time.monotonic() - self.source_last.get(source, 0)))
            if pause > 0:
                time.sleep(pause)
            self.last_request = time.monotonic()
            self.source_last[source] = self.last_request
            self.requests += 1
            try:
                response = self.client.request(method, url, params=params, json=body, headers=headers)
                content = response.content
                # Credentials are never stored, even if a provider echoes one in an error.
                for secret in self.secrets:
                    content = content.replace(secret.encode(), b"REDACTED")
                sha = hashlib.sha256(content).hexdigest()
                directory.mkdir(parents=True, exist_ok=True)
                raw = directory / (sha + "." + extension)
                if not raw.exists() or hashlib.sha256(raw.read_bytes()).hexdigest() != sha:
                    atomic_bytes(raw, content)
                try:
                    rows = record_count(json.loads(content))
                except (ValueError, UnicodeDecodeError):
                    rows = max(0, len(content.splitlines()) - 1) if extension == "csv" else 0
                metadata = {**identity, "status": response.status_code, "fetched_epoch": time.time(),
                            "downloaded_at_utc": utc_now(), "sha256": sha, "file_path": raw.relative_to(self.root).as_posix(), "row_count": rows}
                self.log(source, safe, raw, rows, start=start, end=end, kind="observed" if response.is_success else "source_error",
                         downloaded_at=metadata["downloaded_at_utc"])
                atomic_json(metadata_path, metadata)
                if response.is_success:
                    return content, metadata
                final = f"{source}: HTTP {response.status_code} ({safe})"
                if response.status_code not in {408, 425, 429, 500, 502, 503, 504}:
                    break
                retry_after = response.headers.get("Retry-After", "")
                wait = min(30, float(retry_after)) if retry_after.isdigit() else min(20, 2**attempt)
                if response.status_code == 429:
                    wait = max(wait, min(60, 15 * 2**attempt))
                    if source in self.source_delay:
                        self.source_delay[source] = max(self.source_delay[source], 12)
            except httpx.RequestError as exc:
                final = f"{source}: {type(exc).__name__} ({safe})"
                wait = min(20, 2**attempt)
            if attempt + 1 < self.attempts:
                time.sleep(wait)
        raise SourceError(final or f"{source}: download failed")

    def json(self, source, url, **kwargs):
        method = kwargs.pop("method", "GET")
        raw, metadata = self.request(source, method, url, **kwargs)
        try:
            return json.loads(raw), metadata
        except ValueError as exc:
            raise SourceError(f"{source}: response is not valid JSON") from exc

    def frame(self, name, frame, source, endpoint, *, start="", end="", kind="observed", lineage=None):
        if not re.fullmatch(r"[a-z0-9_-]+", name):
            raise ValueError("Unsafe dataset name")
        path = self.root / "data/processed" / (name + ".parquet")
        content = frame.to_parquet(index=False)
        sha = hashlib.sha256(content).hexdigest()
        version = self.root / "data/processed/_versions" / name / (sha + ".parquet")
        if not version.exists():
            atomic_bytes(version, content)
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            atomic_bytes(path, content)
        self.log(source, endpoint, version, len(frame), start=start, end=end, kind=kind)
        entry = self.log(source, endpoint, path, len(frame), start=start, end=end, kind=kind)
        entry["lineage"] = lineage or []
        self.artifacts[version.relative_to(self.root).as_posix()]["lineage"] = lineage or []
        return entry

    def checkpoint(self, name, state):
        path = self.root / "data/interim/checkpoints" / (name + ".json")
        atomic_json(path, state)

    def reference(self, path):
        """Prefer immutable processed inputs when recording derived lineage."""
        path = Path(path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        version = self.root / "data/processed/_versions" / path.stem / (sha + path.suffix)
        return (version if version.exists() else path).relative_to(self.root).as_posix()

    def checkpoint_value(self, name):
        path = self.root / "data/interim/checkpoints" / (name + ".json")
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def coverage_row(source, dataset, status, frame=None, note="", **extra):
    row = {"source": source, "dataset": dataset, "status": status, "rows": 0, "start": None, "end": None, "note": note, **extra}
    if frame is not None and len(frame):
        row["rows"] = len(frame)
        time_column = "timestamp" if "timestamp" in frame else ("data_asof" if "data_asof" in frame else None)
        if time_column:
            times = pd.to_datetime(frame[time_column], utc=True)
            row["start"], row["end"] = times.min().isoformat(), times.max().isoformat()
    return row
