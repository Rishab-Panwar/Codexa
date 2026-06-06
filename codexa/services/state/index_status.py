import threading


class IndexStatusRegistry:
    """In-memory tracker for repo indexing progress within a process.

    Status values: "processing", "ready", "failed". Persisted indexes loaded
    from disk on startup are not tracked here — the status endpoint falls back
    to the retriever/state store for those.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status: dict[str, dict] = {}

    def set(self, repo_id: str, status: str, **extra: object) -> None:
        with self._lock:
            self._status[repo_id] = {"status": status, **extra}

    def get(self, repo_id: str) -> dict | None:
        with self._lock:
            entry = self._status.get(repo_id)
            return dict(entry) if entry else None
