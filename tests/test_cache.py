"""Tests for the content-addressable render cache."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pidraw.cache import CacheManager, CacheStats


class TestCacheManager:
    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.cache = CacheManager(cache_dir=self.tmp_dir)

    def teardown_method(self) -> None:
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_set_and_get(self) -> None:
        self.cache.set("source1", "<svg></svg>")
        assert self.cache.get("source1") == "<svg></svg>"

    def test_get_miss(self) -> None:
        assert self.cache.get("nonexistent") is None

    def test_get_with_language(self) -> None:
        self.cache.set("source", "<svg></svg>", language="mermaid")
        assert self.cache.get("source", language="mermaid") == "<svg></svg>"
        assert self.cache.get("source") is None

    def test_clear(self) -> None:
        self.cache.set("a", "<svg>a</svg>")
        self.cache.set("b", "<svg>b</svg>")
        self.cache.clear()
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None

    def test_remove(self) -> None:
        self.cache.set("x", "<svg>x</svg>")
        assert self.cache.remove("x") is True
        assert self.cache.get("x") is None
        assert self.cache.remove("x") is False

    def test_stats_empty(self) -> None:
        stats = self.cache.stats()
        assert isinstance(stats, CacheStats)

    def test_stats_after_operations(self) -> None:
        self.cache.set("s1", "<svg>1</svg>")
        self.cache.set("s2", "<svg>2</svg>")
        self.cache.get("s1")
        self.cache.get("s1")
        self.cache.get("s3")
        stats = self.cache.stats()
        assert stats.memory_hits >= 2
        assert stats.memory_misses >= 1
        assert stats.entries >= 2

    def test_ttl_expiry(self) -> None:
        import time

        cache = CacheManager(ttl_seconds=0.1)
        cache.set("tmp", "<svg>tmp</svg>")
        assert cache.get("tmp") == "<svg>tmp</svg>"
        time.sleep(0.15)
        assert cache.get("tmp") is None

    def test_memory_only_cache(self) -> None:
        mem_cache = CacheManager(cache_dir=None)
        mem_cache.set("k", "<svg>v</svg>")
        assert mem_cache.get("k") == "<svg>v</svg>"

    def test_disk_persistence(self) -> None:
        self.cache.set("persist", "<svg>persist</svg>")
        # Create a new cache pointing to the same dir
        cache2 = CacheManager(cache_dir=self.tmp_dir)
        assert cache2.get("persist") == "<svg>persist</svg>"

    def test_content_key_different_for_language(self) -> None:
        self.cache.set("same", "<svg>A</svg>", language="mermaid")
        self.cache.set("same", "<svg>B</svg>", language="graphviz")
        a = self.cache.get("same", language="mermaid")
        b = self.cache.get("same", language="graphviz")
        assert a == "<svg>A</svg>"
        assert b == "<svg>B</svg>"

    def test_max_memory_entries_eviction(self) -> None:
        small_cache = CacheManager(cache_dir=None, max_memory_entries=3)
        for i in range(10):
            small_cache.set(f"k{i}", f"<svg>{i}</svg>")
        # Only 3 should remain
        stats = small_cache.stats()
        assert stats.entries <= 3


class TestCacheDiskFailure:
    def test_corrupted_disk_entry(self) -> None:
        tmp = tempfile.mkdtemp()
        try:
            (Path(tmp) / "deadbeef.json").write_text("not json", encoding="utf-8")
            cache = CacheManager(cache_dir=tmp)
            assert cache.get("anything") is None
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_cache_dir(self) -> None:
        import tempfile

        d = tempfile.mkdtemp()
        os.rmdir(d)
        cache = CacheManager(cache_dir=d)
        cache.set("k", "<svg/>")
        assert cache.get("k") == "<svg/>"
        import shutil

        shutil.rmtree(d, ignore_errors=True)
