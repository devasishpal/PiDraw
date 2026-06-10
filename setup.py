"""Setup script — auto-installs CLI tools after pip install."""

import subprocess
import sys

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def _run_pidraw_setup():
    try:
        subprocess.run(
            [sys.executable, "-m", "pidraw", "setup"],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except Exception:
        pass


class PostInstallCommand(install):
    def run(self):
        install.run(self)
        _run_pidraw_setup()


class PostDevelopCommand(develop):
    def run(self):
        develop.run(self)
        _run_pidraw_setup()


setup(
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    }
)
