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


def _make_repo(tmp_path):
    """Build a minimal fake upstream tree."""
    repo = tmp_path / "repo"
    ps_user = repo / "docs/configs/shell/powershell/user"
    ps_root = repo / "docs/configs/shell/powershell/root"
    ps_user.mkdir(parents=True)
    ps_root.mkdir(parents=True)
    (ps_user / "Microsoft.PowerShell_profile.ps1").write_text("# user\n# /home/pwnedlabs/.config\n")
    (ps_root / "Microsoft.PowerShell_profile.ps1").write_text("# root\n")
    custom = repo / "docs/configs/launchers/custom"
    custom.mkdir(parents=True)
    (custom / "menulibre-pmapper.desktop").write_text(
        "Exec=xfce4-terminal --command \"zsh -i -c '/opt/aws_tools/pmapper/pmapper_launcher.sh; exec zsh'\"\n")
    aws = repo / "docs/configs/launchers/aws"
    aws.mkdir(parents=True)
    (aws / "pmapper_launcher.sh").write_text("#!/bin/zsh\necho hi\n")
    (aws / "unmapped_launcher.sh").write_text("#!/bin/zsh\n")
    return repo


def test_install_powershell_profiles_user_to_home(tmp_path):
    repo = _make_repo(tmp_path)
    home = tmp_path / "home"
    written = cfg.install_powershell_profiles(repo, home=home)
    user_dest = home / ".config/powershell/Microsoft.PowerShell_profile.ps1"
    assert str(user_dest) in written
    assert user_dest.exists()
    assert "/home/pwnedlabs" not in user_dest.read_text()


def test_launcher_dest_map_parses_exec(tmp_path):
    repo = _make_repo(tmp_path)
    m = cfg._launcher_dest_map(repo)
    assert m["pmapper_launcher.sh"] == "/opt/aws_tools/pmapper/pmapper_launcher.sh"


def test_install_launchers_places_mapped_only(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    written = {}
    monkeypatch.setattr(cfg, "_write_file",
                        lambda data, dest, mode=0o644: written.setdefault(str(dest), mode) or True)
    placed = cfg.install_launchers(repo)
    assert "/opt/aws_tools/pmapper/pmapper_launcher.sh" in placed
    assert written["/opt/aws_tools/pmapper/pmapper_launcher.sh"] == 0o755
    # unmapped_launcher.sh has no .desktop dest → skipped
    assert not any("unmapped" in p for p in placed)
