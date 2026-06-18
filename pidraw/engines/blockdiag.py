"""BlockDiag renderer — block diagrams, architecture diagrams.

Supports:
  - blockdiag: block diagrams
  - seqdiag: sequence diagrams
  - actdiag: activity diagrams
  - nwdiag: network diagrams
  - packetdiag: packet diagrams
  - rackdiag: rack diagrams

Each requires the corresponding Python package.
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError


class BlockDiagRenderer(BaseRenderer):
    """Renderer for blockdiag (block diagrams) — uses the blockdiag package."""

    name = "blockdiag"
    _available: bool = False

    def __init__(self) -> None:
        try:
            import blockdiag  # noqa: F401
            import blockdiag.command  # noqa: F401
            self._available = True
        except ImportError:
            raise EngineNotAvailableError(
                "blockdiag",
                setup_command="pip install blockdiag",
            )

    def render(self, source: str) -> str:
        if not self._available:
            raise EngineNotAvailableError(
                "blockdiag",
                setup_command="pip install blockdiag",
            )
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_blockdiag_")
            input_path = os.path.join(tmp_dir, "input.diag")
            output_path = os.path.join(tmp_dir, "output.svg")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            from blockdiag.command import main as blockdiag_main

            blockdiag_main(["-T", "svg", "-o", output_path, input_path])

            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    return f.read()
            raise RenderError("blockdiag", "No output file generated")
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("blockdiag", f"Rendering failed: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil
                try:
                    shutil.rmtree(tmp_dir)
                except OSError:
                    pass


class SeqDiagRenderer(BaseRenderer):
    """Renderer for seqdiag — uses the seqdiag package."""

    name = "seqdiag"
    _available: bool = False

    def __init__(self) -> None:
        try:
            import seqdiag  # noqa: F401
            self._available = True
        except ImportError:
            raise EngineNotAvailableError(
                "seqdiag",
                setup_command="pip install seqdiag",
            )

    def render(self, source: str) -> str:
        if not self._available:
            raise EngineNotAvailableError(
                "seqdiag",
                setup_command="pip install seqdiag",
            )
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_seqdiag_")
            input_path = os.path.join(tmp_dir, "input.diag")
            output_path = os.path.join(tmp_dir, "output.svg")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            from seqdiag.command import main as seqdiag_main

            seqdiag_main(["-T", "svg", "-o", output_path, input_path])

            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    return f.read()
            raise RenderError("seqdiag", "No output file generated")
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("seqdiag", f"Rendering failed: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil
                try:
                    shutil.rmtree(tmp_dir)
                except OSError:
                    pass


class ActDiagRenderer(BaseRenderer):
    """Renderer for actdiag — uses the actdiag package."""

    name = "actdiag"
    _available: bool = False

    def __init__(self) -> None:
        try:
            import actdiag  # noqa: F401
            self._available = True
        except ImportError:
            raise EngineNotAvailableError(
                "actdiag",
                setup_command="pip install actdiag",
            )

    def render(self, source: str) -> str:
        if not self._available:
            raise EngineNotAvailableError(
                "actdiag",
                setup_command="pip install actdiag",
            )
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_actdiag_")
            input_path = os.path.join(tmp_dir, "input.diag")
            output_path = os.path.join(tmp_dir, "output.svg")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            from actdiag.command import main as actdiag_main

            actdiag_main(["-T", "svg", "-o", output_path, input_path])

            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    return f.read()
            raise RenderError("actdiag", "No output file generated")
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("actdiag", f"Rendering failed: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil
                try:
                    shutil.rmtree(tmp_dir)
                except OSError:
                    pass


class NwDiagRenderer(BaseRenderer):
    """Renderer for nwdiag — uses the nwdiag package."""

    name = "nwdiag"
    _available: bool = False

    def __init__(self) -> None:
        try:
            import nwdiag  # noqa: F401
            self._available = True
        except ImportError:
            raise EngineNotAvailableError(
                "nwdiag",
                setup_command="pip install nwdiag",
            )

    def render(self, source: str) -> str:
        if not self._available:
            raise EngineNotAvailableError(
                "nwdiag",
                setup_command="pip install nwdiag",
            )
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_nwdiag_")
            input_path = os.path.join(tmp_dir, "input.diag")
            output_path = os.path.join(tmp_dir, "output.svg")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            from nwdiag.command import main as nwdiag_main

            nwdiag_main(["-T", "svg", "-o", output_path, input_path])

            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    return f.read()
            raise RenderError("nwdiag", "No output file generated")
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("nwdiag", f"Rendering failed: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil
                try:
                    shutil.rmtree(tmp_dir)
                except OSError:
                    pass
