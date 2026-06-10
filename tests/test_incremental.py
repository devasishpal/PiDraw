"""Tests for the incremental renderer."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pidraw.incremental import FileState, IncrementalRenderer


class TestIncrementalRenderer:
    def setup_method(self) -> None:
        self.state_dir = tempfile.mkdtemp()
        self.renderer = IncrementalRenderer(state_dir=self.state_dir)

    def teardown_method(self) -> None:
        import shutil

        shutil.rmtree(self.state_dir, ignore_errors=True)

    def test_needs_render_new_file(self) -> None:
        p = Path(self.state_dir) / "test.mmd"
        p.write_text("graph TD", encoding="utf-8")
        assert self.renderer.needs_render(str(p)) is True

    def test_needs_render_after_record(self) -> None:
        p = Path(self.state_dir) / "test.mmd"
        p.write_text("graph TD", encoding="utf-8")
        self.renderer.record_render(str(p), "graph TD", "<svg/>")
        assert self.renderer.needs_render(str(p)) is False

    def test_needs_render_after_change(self) -> None:
        p = Path(self.state_dir) / "test.mmd"
        p.write_text("graph TD", encoding="utf-8")
        self.renderer.record_render(str(p), "graph TD", "<svg/>")
        p.write_text("graph LR", encoding="utf-8")
        assert self.renderer.needs_render(str(p)) is True

    def test_get_state(self) -> None:
        p = Path(self.state_dir) / "test.mmd"
        p.write_text("graph TD", encoding="utf-8")
        self.renderer.record_render(str(p), "graph TD", "<svg/>")
        state = self.renderer.get_state(str(p))
        assert state is not None
        assert isinstance(state, FileState)
        assert state.source_hash
        assert state.render_hash
        assert state.last_rendered > 0

    def test_clear_state_single(self) -> None:
        p = Path(self.state_dir) / "test.mmd"
        p.write_text("graph TD", encoding="utf-8")
        self.renderer.record_render(str(p), "graph TD", "<svg/>")
        assert self.renderer.get_state(str(p)) is not None
        self.renderer.clear_state(str(p))
        assert self.renderer.get_state(str(p)) is None

    def test_clear_state_all(self) -> None:
        p1 = Path(self.state_dir) / "a.mmd"
        p2 = Path(self.state_dir) / "b.mmd"
        p1.write_text("A", encoding="utf-8")
        p2.write_text("B", encoding="utf-8")
        self.renderer.record_render(str(p1), "A", "<svg/>")
        self.renderer.record_render(str(p2), "B", "<svg/>")
        self.renderer.clear_state()
        assert self.renderer.get_state(str(p1)) is None
        assert self.renderer.get_state(str(p2)) is None

    def test_stats(self) -> None:
        stats = self.renderer.stats()
        assert stats.files_checked == 0
        assert stats.files_rendered == 0
        assert stats.files_skipped == 0
        assert stats.files_failed == 0

    def test_stats_increment(self) -> None:
        self.renderer.skip_file("x")
        self.renderer.record_failure("y")
        stats = self.renderer.stats()
        assert stats.files_skipped == 1
        assert stats.files_failed == 1

    def test_reset_stats(self) -> None:
        self.renderer.skip_file("x")
        self.renderer.reset_stats()
        stats = self.renderer.stats()
        assert stats.files_skipped == 0

    def test_persistence(self) -> None:
        p = Path(self.state_dir) / "persist.mmd"
        p.write_text("graph TD", encoding="utf-8")
        self.renderer.record_render(str(p), "graph TD", "<svg/>")

        r2 = IncrementalRenderer(state_dir=self.state_dir)
        state = r2.get_state(str(p))
        assert state is not None
        assert state.source_hash
