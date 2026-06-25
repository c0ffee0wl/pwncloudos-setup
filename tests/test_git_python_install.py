from pathlib import Path

import src.updaters.git_python_updater as gpu
from conftest import FakeCompleted


def _make(tmp_path, config, tool_factory, monkeypatch, has_uv):
    tool = tool_factory(
        install_method="git_python",
        github_repo="owner/repo",
        path=tmp_path / "repo",
    )
    updater = gpu.GitPythonUpdater(tool, config)
    # Pretend the clone succeeded and produced a requirements.txt.
    (tmp_path / "repo").mkdir(parents=True)
    (tmp_path / "repo" / "requirements.txt").write_text("requests\n")
    monkeypatch.setattr(updater, "_git_clone",
                        lambda: gpu.UpdateResult(success=True, tool_name=tool.name))
    monkeypatch.setattr(gpu.shutil, "which", lambda n: "/usr/bin/uv" if has_uv else None)
    return updater


def test_install_uses_uv_when_available(tmp_path, config, tool_factory, monkeypatch):
    calls = []
    monkeypatch.setattr(gpu.subprocess, "run",
                        lambda cmd, *a, **k: calls.append(cmd) or FakeCompleted(0))
    updater = _make(tmp_path, config, tool_factory, monkeypatch, has_uv=True)

    result = updater.perform_install()

    assert result.success is True
    req_cmd = next(c for c in calls if "pip" in c and "install" in c)
    assert req_cmd[:4] == ["/usr/bin/uv", "pip", "install", "--system"]
    assert "--break-system-packages" in req_cmd


def test_install_falls_back_to_pip(tmp_path, config, tool_factory, monkeypatch):
    calls = []
    monkeypatch.setattr(gpu.subprocess, "run",
                        lambda cmd, *a, **k: calls.append(cmd) or FakeCompleted(0))
    updater = _make(tmp_path, config, tool_factory, monkeypatch, has_uv=False)

    updater.perform_install()

    req_cmd = next(c for c in calls if "pip" in c and "install" in c)
    assert req_cmd[:3] == ["python3", "-m", "pip"]
    assert "--break-system-packages" in req_cmd


def test_install_falls_back_to_pip_when_uv_fails(tmp_path, config, tool_factory, monkeypatch):
    """When uv is present but exits non-zero, pip must be attempted next."""
    calls = []

    def fake_run(cmd, *a, **k):
        calls.append(cmd)
        # uv command fails (returncode 1), pip command succeeds
        if cmd[0] == "/usr/bin/uv":
            return FakeCompleted(1, stderr="uv error")
        return FakeCompleted(0)

    monkeypatch.setattr(gpu.subprocess, "run", fake_run)
    updater = _make(tmp_path, config, tool_factory, monkeypatch, has_uv=True)

    updater.perform_install()

    # A uv command must have been attempted
    uv_cmds = [c for c in calls if c and c[0] == "/usr/bin/uv"]
    assert uv_cmds, "expected a uv command to be attempted"

    # A pip fallback command must have been attempted after uv failed
    pip_cmds = [c for c in calls if "python3" in c and "-m" in c and "pip" in c]
    assert pip_cmds, "expected a python3 -m pip fallback command after uv failure"
