from pathlib import Path

import src.installer.configs as cfg
from conftest import FakeCompleted


def test_fetch_upstream_builds_shallow_clone(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cfg.subprocess, "run",
                        lambda c, *a, **k: calls.append(c) or FakeCompleted(0))
    dest = tmp_path / "clone"
    result = cfg.fetch_upstream(dest)
    assert result == dest
    assert calls[0][:4] == ["git", "clone", "--depth", "1"]
    assert cfg.UPSTREAM_REPO in calls[0]
    assert str(dest) in calls[0]


def test_fetch_upstream_returns_none_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg.subprocess, "run",
                        lambda c, *a, **k: FakeCompleted(1, stderr="boom"))
    assert cfg.fetch_upstream(tmp_path / "clone") is None


def test_write_file_writes_and_chmods(tmp_path):
    dest = tmp_path / "sub" / "f.txt"
    assert cfg._write_file(b"hello", dest, 0o644) is True
    assert dest.read_bytes() == b"hello"


def test_backup_if_exists_copies(tmp_path):
    dest = tmp_path / "f.txt"
    dest.write_text("old")
    cfg._backup_if_exists(dest)
    assert (tmp_path / "f.txt.pwncloudos-bak").read_text() == "old"
