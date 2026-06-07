"""Content-addressable render cache with memory and disk tiers."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _content_key(source: str, language: str | None = None) -> str:
    """Return a SHA-256 hex digest for the given source (+ optional language)."""
    h = hashlib.sha256()
    if language:
        h.update(language.encode("utf-8"))
        h.update(b"\x00")
    h.update(source.encode("utf-8"))
    return h.hexdigest()


@dataclass
class CacheStats:
    """Statistics for a cache instance."""

    memory_hits: int = 0
    memory_misses: int = 0
    disk_hits: int = 0
    disk_misses: int = 0
    entries: int = 0
    disk_entries: int = 0
    size_bytes: int = 0


@dataclass
class CacheEntry:
    """A single cache entry."""

    svg: str
    rendered_at: float = 0.0
    source_hash: str = ""
    language: str = ""


class CacheManager:
    """Two-tier render cache (memory-first, disk-backed).

    Parameters
    ----------
    cache_dir : str or None
        Directory for the disk cache.  ``None`` disables the disk tier.
    ttl_seconds : float
        Time-to-live for entries.  ``0`` means no expiry.
    max_memory_entries : int
        Maximum number of entries held in memory (LRU-eviction).
        ``0`` means unlimited.

    """

    def __init__(
        self,
        cache_dir: str | None = None,
        ttl_seconds: float = 0.0,
        max_memory_entries: int = 10_000,
    ) -> None:
        self._cache_dir: str | None = cache_dir
        self._ttl: float = ttl_seconds
        self._max_mem: int = max_memory_entries
        self._memory: dict[str, CacheEntry] = {}
        self._access_order: list[str] = []
        self._stats = CacheStats()

        if cache_dir is not None:
            os.makedirs(cache_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, source: str, language: str | None = None) -> Optional[str]:
        """Retrieve cached SVG.  Returns ``None`` on miss."""
        key = _content_key(source, language)

        # Memory tier
        entry = self._memory.get(key)
        if entry is not None:
            if self._is_expired(entry):
                del self._memory[key]
                self._prune_access(key)
            else:
                self._stats.memory_hits += 1
                self._touch(key)
                return entry.svg

        self._stats.memory_misses += 1

        # Disk tier
        if self._cache_dir is not None:
            svg = self._read_disk(key)
            if svg is not None:
                self._stats.disk_hits += 1
                self._to_memory(key, svg)
                return svg
            self._stats.disk_misses += 1

        return None

    def set(
        self,
        source: str,
        svg: str,
        language: str | None = None,
    ) -> None:
        """Store an SVG in the cache."""
        key = _content_key(source, language)
        entry = CacheEntry(
            svg=svg,
            rendered_at=time.time(),
            source_hash=key,
            language=language or "",
        )
        self._to_memory(key, entry.svg)
        if self._cache_dir is not None:
            self._write_disk(key, entry)

    def clear(self) -> None:
        """Clear both memory and disk cache."""
        self._memory.clear()
        self._access_order.clear()
        self._stats = CacheStats()
        if self._cache_dir is not None:
            for f in Path(self._cache_dir).iterdir():
                if f.suffix == ".json":
                    f.unlink()

    def stats(self) -> CacheStats:
        """Return current cache statistics."""
        self._stats.entries = len(self._memory)
        if self._cache_dir is not None:
            disk_entries = 0
            size = 0
            for f in Path(self._cache_dir).iterdir():
                if f.suffix == ".json":
                    disk_entries += 1
                    size += f.stat().st_size
            self._stats.disk_entries = disk_entries
            self._stats.size_bytes = size
        return self._stats

    def remove(self, source: str, language: str | None = None) -> bool:
        """Remove a specific entry.  Returns ``True`` if anything was removed."""
        key = _content_key(source, language)
        found = False
        if key in self._memory:
            del self._memory[key]
            self._prune_access(key)
            found = True
        if self._cache_dir is not None:
            disk_path = self._disk_path(key)
            if disk_path.exists():
                disk_path.unlink()
                found = True
        return found

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _is_expired(self, entry: CacheEntry) -> bool:
        if self._ttl <= 0:
            return False
        return (time.time() - entry.rendered_at) > self._ttl

    def _touch(self, key: str) -> None:
        self._prune_access(key)
        self._access_order.append(key)

    def _prune_access(self, key: str) -> None:
        try:
            self._access_order.remove(key)
        except ValueError:
            pass

    def _to_memory(self, key: str, svg: str) -> None:
        if self._max_mem > 0 and len(self._memory) >= self._max_mem:
            oldest = self._access_order.pop(0)
            self._memory.pop(oldest, None)
        self._memory[key] = CacheEntry(svg=svg, rendered_at=time.time())
        self._touch(key)

    def _disk_path(self, key: str) -> Path:
        path = Path(self._cache_dir) / f"{key}.json" if self._cache_dir else Path()
        return path

    def _write_disk(self, key: str, entry: CacheEntry) -> None:
        path = self._disk_path(key)
        data = {
            "svg": entry.svg,
            "rendered_at": entry.rendered_at,
            "source_hash": entry.source_hash,
            "language": entry.language,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _read_disk(self, key: str) -> Optional[str]:
        path = self._disk_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = CacheEntry(**data)
            if self._is_expired(entry):
                path.unlink()
                return None
            return entry.svg
        except (json.JSONDecodeError, KeyError, TypeError):
            path.unlink(missing_ok=True)
            return None
