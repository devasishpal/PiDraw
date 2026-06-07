"""Incremental renderer — only re-render changed files.

Tracks source content hashes so unchanged files are served from
cache or skipped entirely.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from pidraw.cache import CacheManager


@dataclass
class FileState:
    """Persistent state for a tracked file."""

    source_hash: str = ""
    render_hash: str = ""
    last_rendered: float = 0.0
    file_size: int = 0


@dataclass
class IncrementalStats:
    """Statistics for incremental build operations."""

    files_checked: int = 0
    files_rendered: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    elapsed_ms: float = 0.0


class IncrementalRenderer:
    """Renders only files whose content has changed.

    Parameters
    ----------
    state_dir : str or None
        Directory for persistent state.  ``None`` disables persistence.
    cache : CacheManager or None
        Optional render cache (avoids re-rendering even for cache hits).

    """

    def __init__(
        self,
        state_dir: str | None = None,
        cache: CacheManager | None = None,
    ) -> None:
        self._state_dir = state_dir
        self._cache = cache
        self._state: dict[str, FileState] = {}
        self._stats = IncrementalStats()

        if state_dir is not None:
            os.makedirs(state_dir, exist_ok=True)
            self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def needs_render(self, file_path: str, source: str | None = None) -> bool:
        """Check if a file needs to be re-rendered.

        Parameters
        ----------
        file_path :
            Path to the source file.
        source :
            Optional pre-read source.  If ``None``, the file is read.

        Returns
        -------
        bool
            ``True`` if the file has changed since last render.

        """
        self._stats.files_checked += 1
        path = Path(file_path)
        if not path.is_file():
            return True

        current_hash = self._compute_source_hash(source or path.read_text(encoding="utf-8-sig"))
        state = self._state.get(str(path))
        if state is None:
            return True

        return state.source_hash != current_hash

    def record_render(
        self,
        file_path: str,
        source: str,
        svg: str,
    ) -> None:
        """Record a successful render."""
        path = str(Path(file_path))
        source_hash = self._compute_source_hash(source)
        render_hash = self._compute_source_hash(svg)

        self._state[path] = FileState(
            source_hash=source_hash,
            render_hash=render_hash,
            last_rendered=time.time(),
            file_size=len(source.encode("utf-8")),
        )
        self._stats.files_rendered += 1
        self._save_state()

    def skip_file(self, file_path: str) -> None:
        """Mark a file as skipped (no render needed)."""
        self._stats.files_skipped += 1

    def record_failure(self, file_path: str) -> None:
        """Record a render failure."""
        self._stats.files_failed += 1

    def get_state(self, file_path: str) -> FileState | None:
        """Return the stored state for a file, or ``None``."""
        return self._state.get(str(Path(file_path)))

    def clear_state(self, file_path: str | None = None) -> None:
        """Clear state for one file, or all files if *file_path* is ``None``."""
        if file_path is None:
            self._state.clear()
        else:
            self._state.pop(str(Path(file_path)), None)
        self._save_state()

    def stats(self) -> IncrementalStats:
        """Return current incremental build statistics."""
        return self._stats

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = IncrementalStats()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_source_hash(source: str) -> str:
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def _state_path(self) -> Path:
        assert self._state_dir is not None
        return Path(self._state_dir) / "incremental_state.json"

    def _load_state(self) -> None:
        if self._state_dir is None:
            return
        sp = self._state_path()
        if not sp.exists():
            return
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
            for k, v in data.items():
                self._state[k] = FileState(**v)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    def _save_state(self) -> None:
        if self._state_dir is None:
            return
        data = {k: v.__dict__ for k, v in self._state.items()}
        self._state_path().write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
