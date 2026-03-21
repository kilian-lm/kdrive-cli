"""Migration logging via kDrive — stores JSON checkpoint files."""

import json
import time
from datetime import datetime, timezone


class MigrationLog:
    """Stores migration checkpoints as JSON files on kDrive."""

    LOG_DIR_NAME = "_migration_logs"

    def __init__(self, kdrive_client, drive_id: int, parent_dir_id: int = 5):
        self.kdrive = kdrive_client
        self.drive_id = drive_id
        self.parent_dir_id = parent_dir_id
        self._log_dir_id: int | None = None

    @property
    def log_dir_id(self) -> int:
        if self._log_dir_id is None:
            existing = self.kdrive.list_files(self.drive_id, self.parent_dir_id)
            match = next(
                (f for f in existing if f.get("name") == self.LOG_DIR_NAME and f.get("type") == "dir"),
                None,
            )
            if match:
                self._log_dir_id = match["id"]
            else:
                d = self.kdrive.create_directory(self.drive_id, self.parent_dir_id, self.LOG_DIR_NAME)
                self._log_dir_id = d["id"]
        return self._log_dir_id

    def _run_dir(self, run_id: str) -> int:
        existing = self.kdrive.list_files(self.drive_id, self.log_dir_id)
        match = next(
            (f for f in existing if f.get("name") == run_id and f.get("type") == "dir"),
            None,
        )
        if match:
            return match["id"]
        d = self.kdrive.create_directory(self.drive_id, self.log_dir_id, run_id)
        return d["id"]

    def start_run(self, source: str, destination: str, run_id: str | None = None) -> "MigrationRun":
        if run_id is None:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return MigrationRun(self, run_id, source, destination)

    def list_runs(self) -> list[dict]:
        return self.kdrive.list_files(self.drive_id, self.log_dir_id)

    def get_latest_checkpoint(self, run_id: str) -> dict | None:
        dir_id = self._run_dir(run_id)
        files = self.kdrive.list_files(self.drive_id, dir_id)
        checkpoints = [f for f in files if f.get("name", "").startswith("checkpoint_")]
        if not checkpoints:
            return None
        latest = max(checkpoints, key=lambda f: f.get("last_modified_at", 0))
        resp = self.kdrive.download_file(self.drive_id, latest["id"])
        return json.loads(resp.content)


class MigrationRun:
    """Tracks a single migration run with checkpoints and a final summary."""

    def __init__(self, log: MigrationLog, run_id: str, source: str, destination: str):
        self.log = log
        self.run_id = run_id
        self.source = source
        self.destination = destination
        self._dir_id: int | None = None
        self.stats = {"ok": 0, "skip": 0, "err": 0, "bytes": 0, "exist": 0}
        self.errors: list[dict] = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._checkpoint_seq = 0

    @property
    def dir_id(self) -> int:
        if self._dir_id is None:
            self._dir_id = self.log._run_dir(self.run_id)
        return self._dir_id

    def _upload_json(self, filename: str, data: dict):
        content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        try:
            self.log.kdrive.upload_file(
                self.log.drive_id, self.dir_id, filename, content, conflict="version",
            )
        except RuntimeError:
            # If version conflict not supported, try overwrite
            self.log.kdrive.upload_file(
                self.log.drive_id, self.dir_id, filename, content, conflict="rename",
            )

    def record_ok(self, path: str, size: int):
        self.stats["ok"] += 1
        self.stats["bytes"] += size

    def record_skip(self, path: str, reason: str = "already_exists"):
        self.stats["skip"] += 1

    def record_exist(self, path: str):
        self.stats["exist"] += 1

    def record_error(self, path: str, error: str):
        self.stats["err"] += 1
        self.errors.append({"path": path, "error": error, "time": datetime.now(timezone.utc).isoformat()})

    def checkpoint(self, last_processed: str, total: int, current: int):
        """Save a checkpoint every N files for resume capability."""
        self._checkpoint_seq += 1
        data = {
            "run_id": self.run_id,
            "source": self.source,
            "destination": self.destination,
            "started_at": self.started_at,
            "checkpoint_at": datetime.now(timezone.utc).isoformat(),
            "seq": self._checkpoint_seq,
            "progress": {"current": current, "total": total},
            "last_processed": last_processed,
            "stats": self.stats.copy(),
        }
        filename = f"checkpoint_{self._checkpoint_seq:04d}.json"
        self._upload_json(filename, data)

    def finish(self) -> dict:
        """Write final summary."""
        summary = {
            "run_id": self.run_id,
            "source": self.source,
            "destination": self.destination,
            "started_at": self.started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "stats": self.stats,
            "errors": self.errors,
        }
        self._upload_json("summary.json", summary)
        return summary
