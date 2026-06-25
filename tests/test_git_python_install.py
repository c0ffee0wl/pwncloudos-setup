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
    assert req_cmd[:4] == ["uv", "pip", "install", "--system"]
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
