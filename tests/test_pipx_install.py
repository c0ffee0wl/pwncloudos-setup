"""Tests for PipxUpdater install behaviour with pipx_source and pypi_name."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.updaters.pipx_updater import PipxUpdater
from conftest import FakeCompleted


EMPTY_VENVS_JSON = json.dumps({"venvs": {}})


def make_pipx_updater(tool_factory, config, **tool_kwargs):
    defaults = dict(
        name="iamgraph",
        install_method="pipx",
        path=Path("~/.local/bin/iamgraph"),
        pypi_name="iamgraph",
    )
    defaults.update(tool_kwargs)
    tool = tool_factory(**defaults)
    return PipxUpdater(tool, config)


class TestPipxInstallWithSource:
    """Tool with pipx_source set and not yet installed installs from git URL."""

    def test_fresh_install_uses_git_url(self, tool_factory, config):
        """perform_update issues 'pipx install git+https://...' when pipx_source is set."""
        updater = make_pipx_updater(
            tool_factory,
            config,
            pipx_source="git+https://github.com/WithSecureLabs/IAMGraph",
        )

        with patch("subprocess.run") as mock_run:
            # pipx list --json → empty venvs (not installed)
            mock_run.return_value = FakeCompleted(
                returncode=0,
                stdout=EMPTY_VENVS_JSON,
            )
            result = updater.perform_update()

        # Collect all recorded calls
        calls = [call[0][0] for call in mock_run.call_args_list]

        # There must be at least one call containing the git URL
        install_calls = [
            cmd for cmd in calls
            if "install" in cmd and any("git+https://github.com/WithSecureLabs/IAMGraph" in arg for arg in cmd)
        ]
        assert install_calls, (
            f"Expected a 'pipx install git+https://github.com/WithSecureLabs/IAMGraph' call; "
            f"recorded commands: {calls}"
        )

    def test_fresh_install_command_structure(self, tool_factory, config):
        """The install command is ['pipx', 'install', 'git+https://...']."""
        updater = make_pipx_updater(
            tool_factory,
            config,
            pipx_source="git+https://github.com/WithSecureLabs/IAMGraph",
        )

        captured = []

        def fake_run(cmd, **kwargs):
            captured.append(cmd)
            return FakeCompleted(returncode=0, stdout=EMPTY_VENVS_JSON)

        with patch("subprocess.run", side_effect=fake_run):
            updater.perform_update()

        install_cmd = next(
            (cmd for cmd in captured if len(cmd) >= 2 and cmd[:2] == ["pipx", "install"]),
            None,
        )
        assert install_cmd is not None, f"No 'pipx install' call found; calls: {captured}"
        assert install_cmd[2] == "git+https://github.com/WithSecureLabs/IAMGraph", (
            f"Expected git URL as install target, got: {install_cmd[2]}"
        )


class TestPipxInstallWithoutSource:
    """Tool WITHOUT pipx_source falls back to pypi_name for install."""

    def test_fresh_install_uses_pypi_name(self, tool_factory, config):
        """perform_update issues 'pipx install <pypi_name>' when no pipx_source."""
        updater = make_pipx_updater(
            tool_factory,
            config,
            name="pacu",
            pypi_name="pacu",
            path=Path("~/.local/bin/pacu"),
            # No pipx_source field — defaults to None
        )

        captured = []

        def fake_run(cmd, **kwargs):
            captured.append(cmd)
            return FakeCompleted(returncode=0, stdout=EMPTY_VENVS_JSON)

        with patch("subprocess.run", side_effect=fake_run):
            updater.perform_update()

        install_cmd = next(
            (cmd for cmd in captured if len(cmd) >= 2 and cmd[:2] == ["pipx", "install"]),
            None,
        )
        assert install_cmd is not None, f"No 'pipx install' call found; calls: {captured}"
        assert install_cmd[2] == "pacu", (
            f"Expected 'pacu' as install target (pypi_name), got: {install_cmd[2]}"
        )
        assert "git+" not in install_cmd[2], "Should NOT use a git URL when pipx_source is absent"
