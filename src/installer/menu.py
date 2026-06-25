"""Install PwnCloudOS desktop menu entries (DE-only), mirroring category submenus."""

import io
import logging
import os
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import List, Optional

from .configs import _sudo_write

logger = logging.getLogger('pwncloudos-sync')

PACK_REL = "docs/configs/menulibre/pwncloudos-menulibre-profile-pack.tar.gz"
ICONS_REL = "docs/_static/icons"
ICONS_DEST = Path("/usr/share/pwncloudos/icons")
VENDOR_PREFIX = "pwncloudos-"


def has_desktop_environment() -> bool:
    """Best-effort detection of a graphical desktop environment."""
    if os.environ.get("XDG_CURRENT_DESKTOP"):
        return True
    if Path("/usr/share/xsessions").is_dir():
        return True
    return bool(shutil.which("update-desktop-database"))


def install_icons(repo_dir) -> int:
    """Copy PwnCloudOS tool icons to /usr/share/pwncloudos/icons/."""
    src = Path(repo_dir) / ICONS_REL
    if not src.is_dir():
        return 0
    count = 0
    for png in src.glob("*.png"):
        if _sudo_write(png.read_bytes(), ICONS_DEST / png.name, 0o644):
            count += 1
    return count


def _categories(applications: List[Path]) -> List[str]:
    """Collect distinct menulibre-<cat> categories from the .desktop files."""
    cats = []
    for app in applications:
        for line in app.read_text(errors="ignore").splitlines():
            if line.startswith("Categories="):
                for c in line.split("=", 1)[1].split(";"):
                    if c.startswith("menulibre-") and c not in cats:
                        cats.append(c)
    return cats


def _render_menu(categories: List[str]) -> str:
    """Build an XFCE menu-merge file with one submenu per menulibre category."""
    lines = [
        '<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"',
        ' "http://www.freedesktop.org/standards/menu-1.0/menu.dtd">',
        '<Menu>',
        '  <Name>Applications</Name>',
        '  <MergeFile type="parent">/etc/xdg/menus/xfce-applications.menu</MergeFile>',
    ]
    for cat in categories:
        lines += [
            '  <Menu>',
            f'    <Name>{cat}</Name>',
            f'    <Directory>{cat}.directory</Directory>',
            '    <Include>',
            f'      <Category>{cat}</Category>',
            '    </Include>',
            '  </Menu>',
        ]
    lines.append('</Menu>')
    return "\n".join(lines) + "\n"


def install_menu_entries(repo_dir, home: Optional[Path] = None) -> dict:
    """Place menu .desktop + .directory files and a category menu-merge file (DE only)."""
    if not has_desktop_environment():
        logger.info("No desktop environment detected; skipping menu entries")
        return {}

    home = Path(home) if home else Path.home()
    pack = Path(repo_dir) / PACK_REL
    if not pack.exists():
        logger.warning("menulibre profile pack not found upstream; skipping menu entries")
        return {}

    apps_dir = home / ".local/share/applications"
    dirs_dir = home / ".local/share/desktop-directories"
    apps_dir.mkdir(parents=True, exist_ok=True)
    dirs_dir.mkdir(parents=True, exist_ok=True)

    placed_apps: List[Path] = []
    n_dirs = 0
    with tarfile.open(pack, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name
            data = tar.extractfile(member).read()
            if name.startswith("applications/") and name.endswith(".desktop"):
                text = "\n".join(
                    ln for ln in data.decode(errors="ignore").splitlines()
                    if not ln.startswith("OnlyShowIn=")
                )
                base = Path(name).name
                dest = apps_dir / f"{VENDOR_PREFIX}{base}"
                dest.write_text(text + "\n")
                placed_apps.append(dest)
            elif name.startswith("desktop-directories/") and name.endswith(".directory"):
                (dirs_dir / Path(name).name).write_bytes(data)
                n_dirs += 1

    categories = _categories(placed_apps)
    menu_dir = home / ".config/menus/applications-merged"
    menu_dir.mkdir(parents=True, exist_ok=True)
    menu_file = menu_dir / "pwncloudos.menu"
    menu_file.write_text(_render_menu(categories))

    try:
        subprocess.run(["update-desktop-database", str(apps_dir)],
                       capture_output=True, timeout=30)
    except Exception:
        pass

    return {"applications": len(placed_apps), "directories": n_dirs, "menu": str(menu_file)}
