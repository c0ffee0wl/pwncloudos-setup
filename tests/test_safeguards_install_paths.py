from pathlib import Path

from src.core import safeguards


def test_desktop_and_profile_paths_allowed(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    for p in [
        tmp_path / ".local/share/applications/pwncloudos-x.desktop",
        tmp_path / ".local/share/desktop-directories/menulibre-aws.directory",
        tmp_path / ".config/powershell/Microsoft.PowerShell_profile.ps1",
    ]:
        assert safeguards.is_path_allowed(p), p


def test_icons_path_allowed():
    assert safeguards.is_path_allowed(Path("/usr/share/pwncloudos/icons/x.png"))
