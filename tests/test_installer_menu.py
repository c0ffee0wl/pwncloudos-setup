import io
import tarfile
from pathlib import Path

import src.installer.menu as menu


def _make_menulibre_pack(repo: Path):
    pack_dir = repo / "docs/configs/menulibre"
    pack_dir.mkdir(parents=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in [
            ("applications/menulibre-pmapper.desktop",
             b"[Desktop Entry]\nName=PMapper\nOnlyShowIn=XFCE;\nCategories=menulibre-aws;\n"),
            ("desktop-directories/menulibre-aws.directory",
             b"[Desktop Entry]\nName=AWS\n"),
        ]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    (pack_dir / "pwncloudos-menulibre-profile-pack.tar.gz").write_bytes(buf.getvalue())
    return repo


def test_has_desktop_environment_env(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "XFCE")
    assert menu.has_desktop_environment() is True


def test_install_menu_entries_places_and_prefixes(tmp_path, monkeypatch):
    repo = _make_menulibre_pack(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setattr(menu, "has_desktop_environment", lambda: True)
    monkeypatch.setattr(menu.subprocess, "run", lambda *a, **k: None)
    result = menu.install_menu_entries(repo, home=home)
    app = home / ".local/share/applications/pwncloudos-menulibre-pmapper.desktop"
    assert app.exists()
    assert "OnlyShowIn" not in app.read_text()
    assert (home / ".local/share/desktop-directories/menulibre-aws.directory").exists()
    menu_file = home / ".config/menus/applications-merged/pwncloudos.menu"
    assert menu_file.exists()
    assert "menulibre-aws" in menu_file.read_text()
    assert result["applications"] == 1


def test_install_menu_entries_skips_without_de(tmp_path, monkeypatch):
    repo = _make_menulibre_pack(tmp_path / "repo")
    monkeypatch.setattr(menu, "has_desktop_environment", lambda: False)
    result = menu.install_menu_entries(repo, home=tmp_path / "home")
    assert result == {}
