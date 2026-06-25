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


def test_launcher_dest_map_all_exec_forms(tmp_path):
    """All 7 Exec= forms from real PwnCloudOS .desktop files must parse correctly."""
    repo = tmp_path / "repo"
    custom = repo / "docs/configs/launchers/custom"
    custom.mkdir(parents=True)

    cases = [
        # 1. Absolute path inside single-quoted zsh -i -c '...'
        (
            "form1.desktop",
            "Exec=xfce4-terminal --hold --command \"zsh -i -c '/opt/aws_tools/pmapper/pmapper_launcher.sh; exec zsh'\"\n",
            "pmapper_launcher.sh",
            "/opt/aws_tools/pmapper/pmapper_launcher.sh",
        ),
        # 2. bash -c 'cd /opt/dir && ./script'
        (
            "form2.desktop",
            "Exec=xfce4-terminal --hold --command \"bash -c 'cd /opt/azure_tools/bloodhound && ./BloodHound_Launcher.sh; exec bash'\"\n",
            "BloodHound_Launcher.sh",
            "/opt/azure_tools/bloodhound/BloodHound_Launcher.sh",
        ),
        # 3. cd /opt/dir && /usr/bin/zsh ./script
        (
            "form3.desktop",
            "Exec=xfce4-terminal --hold --command \"zsh -i -c 'cd /opt/multi_cloud_tools/s3scanner && /usr/bin/zsh ./s3scanner_launcher.sh; exec zsh'\"\n",
            "s3scanner_launcher.sh",
            "/opt/multi_cloud_tools/s3scanner/s3scanner_launcher.sh",
        ),
        # 4. --working-directory=/opt/dir (unquoted) + --command="./script"
        (
            "form4.desktop",
            "Exec=xfce4-terminal --working-directory=/opt/gcp_tools/username-anarchy --hold --command=\"./username-anarchy_launcher.sh\"\n",
            "username-anarchy_launcher.sh",
            "/opt/gcp_tools/username-anarchy/username-anarchy_launcher.sh",
        ),
        # 5. --working-directory="/opt/dir" (quoted) + ./script inside command
        (
            "form5.desktop",
            "Exec=xfce4-terminal --hold --working-directory=\"/opt/aws_tools/AWeSomeUserFinder\" --command \"zsh -i -c './awesome_userfinder_launcher.sh; exec zsh'\"\n",
            "awesome_userfinder_launcher.sh",
            "/opt/aws_tools/AWeSomeUserFinder/awesome_userfinder_launcher.sh",
        ),
        # 6. Absolute path directly in --command "..." (no shell wrapper)
        (
            "form6.desktop",
            "Exec=xfce4-terminal --hold --command \"/opt/ps_tools/GraphRunner/run_graph_runner.sh\"\n",
            "run_graph_runner.sh",
            "/opt/ps_tools/GraphRunner/run_graph_runner.sh",
        ),
        # 7. Same as 6, different path
        (
            "form7.desktop",
            "Exec=xfce4-terminal --hold --command \"/opt/ps_tools/invoke_modules/run_mfasweep.sh\"\n",
            "run_mfasweep.sh",
            "/opt/ps_tools/invoke_modules/run_mfasweep.sh",
        ),
    ]

    for filename, content, _basename, _dest in cases:
        (custom / filename).write_text(content)

    m = cfg._launcher_dest_map(repo)

    for _filename, _content, basename, dest in cases:
        assert m.get(basename) == dest, f"{basename!r}: expected {dest!r}, got {m.get(basename)!r}"


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
