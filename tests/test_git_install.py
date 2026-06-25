"""Tests for GitUpdater install (clone) behaviour."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.updaters.git_updater import GitUpdater


class FakeCompleted:
    """Stand-in for subprocess.CompletedProcess in tests."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# ── helpers ──────────────────────────────────────────────────────────────────

def make_updater(tool_factory, config, path="/opt/tools/mytool", github_repo="https://github.com/org/mytool"):
    tool = tool_factory(
        name="mytool",
        install_method="git",
        path=Path(path),
        github_repo=github_repo,
    )
    return GitUpdater(tool, config)


# ── _needs_sudo_for_parent ────────────────────────────────────────────────────

class TestNeedsSudoForParent:
    def test_returns_false_when_parent_writable(self, tool_factory, config):
        """User-writable parent → no sudo needed."""
        updater = make_updater(tool_factory, config, path="/tmp/tools/mytool")
        with patch("os.access", return_value=True), \
             patch("os.geteuid", return_value=1000):
            assert updater._needs_sudo_for_parent(Path("/tmp/tools/mytool")) is False

    def test_returns_true_when_parent_not_writable(self, tool_factory, config):
        """/opt parent not writable → sudo required."""
        updater = make_updater(tool_factory, config)
        with patch("os.access", return_value=False), \
             patch("os.geteuid", return_value=1000):
            assert updater._needs_sudo_for_parent(Path("/opt/tools/mytool")) is True

    def test_returns_false_when_root(self, tool_factory, config):
        """Root user never needs sudo."""
        updater = make_updater(tool_factory, config)
        with patch("os.geteuid", return_value=0):
            assert updater._needs_sudo_for_parent(Path("/opt/tools/mytool")) is False


# ── _git_clone ────────────────────────────────────────────────────────────────

class TestGitClone:
    def test_clone_success_without_sudo(self, tool_factory, config):
        """Successful clone in writable dir returns success UpdateResult."""
        updater = make_updater(tool_factory, config, path="/tmp/tools/mytool")

        with patch.object(updater, "_needs_sudo_for_parent", return_value=False), \
             patch("subprocess.run", return_value=FakeCompleted(returncode=0)) as mock_run, \
             patch.object(updater, "get_current_version", return_value="abc1234"):

            result = updater._git_clone()

        assert result.success is True
        assert result.tool_name == "mytool"
        assert result.new_version == "abc1234"
        # Confirm sudo NOT prepended
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[0] != "sudo"
        assert "clone" in called_cmd

    def test_clone_prepends_sudo_for_opt(self, tool_factory, config):
        """Clone into /opt path prepends sudo."""
        updater = make_updater(tool_factory, config)

        with patch.object(updater, "_needs_sudo_for_parent", return_value=True), \
             patch("subprocess.run", return_value=FakeCompleted(returncode=0)) as mock_run, \
             patch.object(updater, "get_current_version", return_value="abc1234"):

            result = updater._git_clone()

        assert result.success is True
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[0] == "sudo"
        assert "clone" in called_cmd

    def test_clone_failure_returns_error(self, tool_factory, config):
        """Failed clone returns failure UpdateResult with stderr."""
        updater = make_updater(tool_factory, config)

        with patch.object(updater, "_needs_sudo_for_parent", return_value=False), \
             patch("subprocess.run", return_value=FakeCompleted(returncode=1, stderr="fatal: repo not found")):

            result = updater._git_clone()

        assert result.success is False
        assert "fatal" in result.error_message

    def test_clone_timeout_returns_error(self, tool_factory, config):
        """Timeout during clone returns failure UpdateResult."""
        updater = make_updater(tool_factory, config)

        with patch.object(updater, "_needs_sudo_for_parent", return_value=False), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 120)):

            result = updater._git_clone()

        assert result.success is False
        assert result.error_message  # some message present


# ── perform_install ───────────────────────────────────────────────────────────

class TestPerformInstall:
    def test_delegates_to_update_when_git_exists(self, tool_factory, config, tmp_path):
        """If .git dir present, perform_install calls perform_update."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        updater = make_updater(tool_factory, config, path=str(tmp_path))

        fake_result = MagicMock()
        with patch.object(updater, "perform_update", return_value=fake_result) as mock_update:
            result = updater.perform_install()

        mock_update.assert_called_once()
        assert result is fake_result

    def test_calls_clone_when_no_git_dir(self, tool_factory, config, tmp_path):
        """If .git dir absent, perform_install calls _git_clone."""
        updater = make_updater(tool_factory, config, path=str(tmp_path))

        fake_result = MagicMock()
        with patch.object(updater, "_git_clone", return_value=fake_result) as mock_clone:
            result = updater.perform_install()

        mock_clone.assert_called_once()
        assert result is fake_result
