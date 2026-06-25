"""Fetch and place PwnCloudOS launcher scripts and PowerShell profiles from upstream."""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('pwncloudos-sync')

UPSTREAM_REPO = "https://github.com/pwnedlabs/pwncloudos.git"


def fetch_upstream(dest_dir=None) -> Optional[Path]:
    """Shallow-clone the upstream pwncloudos repo. Returns the clone path or None."""
    dest = Path(dest_dir) if dest_dir else Path(tempfile.mkdtemp(prefix="pwncloudos-cfg-"))
    cmd = ['git', 'clone', '--depth', '1', UPSTREAM_REPO, str(dest)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return dest
        logger.error(f"Failed to clone upstream configs: {result.stderr.strip()}")
    except Exception as e:
        logger.error(f"Error cloning upstream configs: {e}")
    return None


def _sudo_write(data: bytes, dest: Path, mode: int) -> bool:
    """Write bytes to a root-owned location via sudo."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        subprocess.run(['sudo', 'mkdir', '-p', str(dest.parent)],
                       capture_output=True, timeout=30)
        result = subprocess.run(['sudo', 'cp', tmp_path, str(dest)],
                                capture_output=True, timeout=30)
        subprocess.run(['sudo', 'chmod', oct(mode)[2:], str(dest)],
                       capture_output=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"sudo write to {dest} failed: {e}")
        return False
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _write_file(data: bytes, dest: Path, mode: int = 0o644) -> bool:
    """Write bytes to dest (mkdir parents, chmod). Falls back to sudo on PermissionError."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        os.chmod(dest, mode)
        return True
    except PermissionError:
        return _sudo_write(data, dest, mode)
    except OSError as e:
        logger.error(f"Failed to write {dest}: {e}")
        return False


def _backup_if_exists(dest: Path) -> None:
    """Best-effort timestamp-free backup of an existing file before overwrite."""
    if not dest.exists():
        return
    backup = dest.with_suffix(dest.suffix + ".pwncloudos-bak")
    try:
        shutil.copy2(dest, backup)
    except PermissionError:
        subprocess.run(['sudo', 'cp', '-p', str(dest), str(backup)],
                       capture_output=True, timeout=30)
    except OSError as e:
        logger.warning(f"Could not back up {dest}: {e}")


def install_powershell_profiles(repo_dir, home: Optional[Path] = None) -> List[str]:
    """Install the user and root PowerShell profiles. Never touches .zshrc."""
    repo = Path(repo_dir)
    base = repo / "docs" / "configs" / "shell" / "powershell"
    home = Path(home) if home else Path.home()
    written: List[str] = []

    user_src = base / "user" / "Microsoft.PowerShell_profile.ps1"
    if user_src.exists():
        content = user_src.read_text(errors="ignore").replace("/home/pwnedlabs", str(home))
        dest = home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"
        _backup_if_exists(dest)
        if _write_file(content.encode(), dest, 0o644):
            written.append(str(dest))

    root_src = base / "root" / "Microsoft.PowerShell_profile.ps1"
    if root_src.exists():
        dest = Path("/root/.config/powershell/Microsoft.PowerShell_profile.ps1")
        if _sudo_write(root_src.read_bytes(), dest, 0o644):
            written.append(str(dest))

    return written


def _launcher_dest_map(repo_dir) -> Dict[str, str]:
    """Map launcher basename -> /opt destination, parsed from custom .desktop Exec lines."""
    dest_map: Dict[str, str] = {}
    custom = Path(repo_dir) / "docs" / "configs" / "launchers" / "custom"
    if not custom.is_dir():
        return dest_map
    # Direct absolute path form: '/opt/<cat>/<tool>/<name>_launcher.sh'
    abs_re = re.compile(r"(/opt/\S+?_[Ll]auncher\.sh)")
    # cd-into form: cd /opt/<dir> && ./<name>_Launcher.sh
    cd_re = re.compile(r"cd\s+(/opt/\S+?)\s+&&\s+\./(\S+?_[Ll]auncher\.sh)")
    for desktop in custom.glob("*.desktop"):
        for line in desktop.read_text(errors="ignore").splitlines():
            if not line.startswith("Exec="):
                continue
            for m in abs_re.finditer(line):
                p = m.group(1)
                dest_map[Path(p).name] = p
            m2 = cd_re.search(line)
            if m2:
                fname = m2.group(2)
                dest_map[fname] = f"{m2.group(1)}/{fname}"
    return dest_map


def install_launchers(repo_dir) -> List[str]:
    """Place launcher .sh files at the /opt destinations parsed from .desktop files."""
    dest_map = _launcher_dest_map(repo_dir)
    launchers_dir = Path(repo_dir) / "docs" / "configs" / "launchers"
    placed: List[str] = []
    if not launchers_dir.is_dir():
        return placed
    for cat_dir in launchers_dir.iterdir():
        if not cat_dir.is_dir() or cat_dir.name == "custom":
            continue
        for sh in cat_dir.glob("*.sh"):
            dest = dest_map.get(sh.name)
            if not dest:
                logger.debug(f"No .desktop destination for launcher {sh.name}; skipping")
                continue
            if _write_file(sh.read_bytes(), Path(dest), 0o755):
                placed.append(dest)
    return placed
