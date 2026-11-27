"""
Thread-safe, file-backed job store.

Each job is a JSON file in `<DATA_DIR>/jobs`. Writes are atomic
(temp file + rename) so a crash never leaves a half-written job, and a lock
serialises read-modify-write cycles between the API and worker threads.
"""

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def is_valid_job_id(job_id: str) -> bool:
    return bool(_JOB_ID_RE.match(job_id or ""))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    def __init__(self, data_dir: Path):
        self.jobs_dir = data_dir / "jobs"
        self.uploads_dir = data_dir / "uploads"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, job_id: str) -> Path:
        if not is_valid_job_id(job_id):
            raise KeyError(job_id)
        return self.jobs_dir / f"{job_id}.json"

    def get(self, job_id: str) -> dict[str, Any] | None:
        try:
            path = self._path(job_id)
        except KeyError:
            return None
        with self._lock:
            if not path.is_file():
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    def save(self, job: dict[str, Any]) -> None:
        path = self._path(job["id"])
        with self._lock:
            tmp = path.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(job, f, ensure_ascii=False)
            os.replace(tmp, path)

    def update(self, job_id: str, **fields: Any) -> dict[str, Any]:
        """Atomically merge `fields` into the stored job and return it."""
        with self._lock:
            job = self.get(job_id)
            if job is None:
                raise KeyError(job_id)
            job.update(fields)
            job["updated_at"] = utc_now_iso()
            self.save(job)
            return job

    def cleanup(self, ttl_hours: int) -> int:
        """Delete jobs and uploads older than `ttl_hours`. Returns count removed."""
        if ttl_hours <= 0:
            return 0
        cutoff = time.time() - ttl_hours * 3600
        removed = 0
        with self._lock:
            for directory in (self.jobs_dir, self.uploads_dir):
                for path in directory.iterdir():
                    try:
                        if path.is_file() and path.stat().st_mtime < cutoff:
                            path.unlink()
                            removed += 1
                    except OSError:
                        logger.warning("Could not remove %s", path)
        if removed:
            logger.info("Cleanup removed %d old files", removed)
        return removed

    def mark_interrupted(self) -> None:
        """On startup, fail jobs that were mid-flight when the server stopped."""
        with self._lock:
            for path in self.jobs_dir.glob("*.json"):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        job = json.load(f)
                except (OSError, json.JSONDecodeError):
                    continue
                if job.get("status") in ("queued", "processing"):
                    job["status"] = "error"
                    job["error"] = "Processing was interrupted by a server restart. Please upload again."
                    self.save(job)
