"""Shared pytest fixtures for pwncloudos-sync tests."""
import sys
from pathlib import Path

import pytest

# Make the repo root importable so `import src...` works under pytest.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import Config
from src.tools.registry import Tool


class FakeCompleted:
    """Stand-in for subprocess.CompletedProcess in tests."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def tool_factory():
    def _make(**kwargs):
        defaults = dict(
            name="demo",
            category="aws",
            install_method="git",
            path=Path("/tmp/pwncloudos-test/demo"),
        )
        defaults.update(kwargs)
        return Tool(**defaults)

    return _make
