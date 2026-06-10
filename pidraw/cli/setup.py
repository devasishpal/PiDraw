"""Auto-install missing CLI tools for all 14 diagram formats."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from pidraw.cli.logging import get_logger

logger = get_logger()

_TOOLS_DIR = Path.home() / ".pidraw" / "tools"
_NPM_BIN = Path(os.environ.get("APPDATA", "")) / "npm"

# npm packages needed per format: (language name, npm package, binary to check)
_NPM_PKGS: list[tuple[str, str, str]] = [
    ("nomnoml", "nomnoml", "nomnoml"),
    ("markmap", "markmap-cli", "markmap"),
    ("wavedrom", "wavedrom-cli", "wavedrom-cli"),
    ("vega", "vega-cli", "vg2svg"),
    ("vega-lite", "vega-lite", "vl2svg"),
    ("bpmn", "bpmn-svg-generator", "bpmn-svg"),
    ("playwright", "playwright", "playwright"),
]


def _on_path(name: str) -> bool:
    return shutil.which(name) is not None


def _npm_install(pkg: str) -> bool:
    logger.info("  npm install -g %s ...", pkg)
    try:
        subprocess.run(
            ["npm", "install", "-g", pkg],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        return True
    except Exception as exc:
        logger.error("  npm install %s failed: %s", pkg, exc)
        return False


def _download(url: str, dest: Path, timeout: int = 300) -> None:
    logger.info("  Downloading ...")
    urllib.request.urlretrieve(url, dest)
    logger.info("  Saved to %s", dest)


def _install_playwright_browsers() -> str:
    """Install Playwright Chromium browser."""
    if _on_path("playwright"):
        logger.info("  playwright install chromium ...")
        try:
            subprocess.run(
                ["playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            return "Chromium installed"
        except Exception as exc:
            return f"Playwright browser install failed: {exc}"
    if _NPM_BIN.joinpath("playwright.cmd").is_file():
        npm_playwright = str(_NPM_BIN / "playwright.cmd")
        try:
            subprocess.run(
                [npm_playwright, "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            return "Chromium installed"
        except Exception as exc:
            return f"Playwright browser install failed: {exc}"
    return "Playwright CLI not found; run: npx playwright install chromium"


def _install_structurizr() -> str:
    """Download structurizr-cli and create a wrapper on PATH."""
    install_dir = _TOOLS_DIR / "structurizr"
    install_dir.mkdir(parents=True, exist_ok=True)

    bat = install_dir / "structurizr.bat"
    wrapper = install_dir / "structurizr-cli.cmd"

    if wrapper.is_file():
        return "Already installed"

    zip_path = install_dir / "structurizr-cli.zip"
    url = "https://github.com/structurizr/cli/releases/download/v2025.11.09/structurizr-cli.zip"

    if not bat.is_file():
        try:
            logger.info("  Downloading structurizr-cli (98MB) ...")
            _download(url, zip_path, timeout=600)
        except Exception as exc:
            zip_path.unlink(missing_ok=True)
            return f"Download failed: {exc}"

        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(install_dir)
            zip_path.unlink()
        except Exception as exc:
            return f"Extract failed: {exc}"

    if not bat.is_file():
        return "structurizr.bat not found in zip"

    abs_bat = bat.resolve()
    wrapper_content = f"""@echo off
set SCRIPT_DIR={abs_bat.parent}
java -cp "%SCRIPT_DIR%;%SCRIPT_DIR%\\lib\\*;" com.structurizr.cli.StructurizrCliApplication %*
"""
    if _NPM_BIN.is_dir():
        dest = _NPM_BIN / "structurizr-cli.cmd"
        dest.write_text(wrapper_content, encoding="utf-8")
        logger.info("  Created wrapper at %s", dest)
        return "Installed"
    else:
        wrapper.write_text(wrapper_content, encoding="utf-8")
        return f"Installed at {wrapper} — add {install_dir} to PATH"


def _ensure_pip_deps() -> str:
    """Install pip packages needed for native rendering."""
    try:
        import vl_convert  # noqa: F401

        return "Already installed"
    except ImportError:
        pass
    logger.info("  pip install vl-convert-python ...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "vl-convert-python"],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        return "Installed"
    except Exception as exc:
        return f"pip install failed: {exc}"


def setup_all() -> dict[str, str]:
    """Attempt to install missing CLI tools for all 14 diagram formats.

    Returns dict of language -> result message.
    """
    results: dict[str, str] = {}

    # --- pip deps ---
    results["vl-convert-python"] = _ensure_pip_deps()

    # --- npm packages ---
    for lang, pkg, binary in _NPM_PKGS:
        if _on_path(binary):
            results[lang] = "Already on PATH"
        else:
            ok = _npm_install(pkg)
            if lang == "playwright":
                results[lang] = "Installed via npm" if ok else "npm install failed"
            else:
                results[lang] = "Installed via npm" if ok else "npm install failed"

    # --- Playwright Chromium browser ---
    if _on_path("playwright"):
        results["playwright-chromium"] = _install_playwright_browsers()

    # --- structurizr (Java download) ---
    if _on_path("structurizr-cli") or _on_path("structurizr"):
        results["structurizr"] = "Already on PATH"
    else:
        results["structurizr"] = _install_structurizr()

    return results
