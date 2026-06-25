"""Tests for BinaryUpdater._place_binary sudo fallback and normal path."""
from pathlib import Path

import src.updaters.binary_updater as bu
from conftest import FakeCompleted


def _make_updater(tmp_path, config, tool_factory):
    tool = tool_factory(
        name="azurehound",
        install_method="binary",
        github_repo="BloodHoundAD/AzureHound",
        path=tmp_path / "azurehound",
    )
    return bu.BinaryUpdater(tool, config)


def test_place_binary_uses_sudo_on_permission_error(tmp_path, config, tool_factory, monkeypatch):
    """When copy2 raises PermissionError, _place_binary must fall back to a privileged install."""
    updater = _make_updater(tmp_path, config, tool_factory)

    root_cmds = []

    def fake_copy2(src, dst):
        raise PermissionError("Permission denied: /opt/x/tool")

    def fake_run_as_root(cmd, *a, **k):
        root_cmds.append(cmd)
        return FakeCompleted(0)

    monkeypatch.setattr(bu.shutil, "copy2", fake_copy2)
    monkeypatch.setattr(bu, "run_as_root", fake_run_as_root)
    # mkdir must also be patched so the PermissionError path is reached cleanly
    monkeypatch.setattr(Path, "mkdir", lambda self, **kw: None)

    src_file = tmp_path / "src_binary"
    src_file.write_bytes(b"\x7fELF")

    updater._place_binary(str(src_file), "/opt/x/tool")

    install_cmds = [c for c in root_cmds if "install" in c]
    assert install_cmds, "expected a privileged install command to be issued"
    assert str(src_file) in install_cmds[0]
    assert "/opt/x/tool" in install_cmds[0]


def test_place_binary_normal_path_no_sudo(tmp_path, config, tool_factory, monkeypatch):
    """When the destination is writable, _place_binary must NOT invoke sudo."""
    updater = _make_updater(tmp_path, config, tool_factory)

    copied = []
    sudo_cmds = []

    def fake_copy2(src, dst):
        copied.append((src, dst))

    def fake_chmod(path, mode):
        pass

    def fake_run(cmd, *a, **k):
        sudo_cmds.append(cmd)
        return FakeCompleted(0)

    monkeypatch.setattr(bu.shutil, "copy2", fake_copy2)
    monkeypatch.setattr(bu.os, "chmod", fake_chmod)
    monkeypatch.setattr(bu.subprocess, "run", fake_run)

    src_file = tmp_path / "src_binary"
    src_file.write_bytes(b"\x7fELF")
    dest = tmp_path / "dest" / "tool"

    updater._place_binary(str(src_file), dest)

    assert copied, "expected shutil.copy2 to be called"
    assert not sudo_cmds, "expected no sudo commands on a writable path"
