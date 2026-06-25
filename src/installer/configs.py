"""Fetch and place PwnCloudOS launcher scripts and PowerShell profiles from upstream.

Security note — confinement vs. safeguards.validate_update_target:
  The sync path uses validate_update_target to PROTECT launcher/.desktop paths from
  accidental overwrite by the updater.  The installer path is the opposite: it must
  CREATE those very paths.  Therefore install_launchers and install_icons use the
  local _confined() helper to restrict writes to explicit roots (/opt,
  /usr/share/pwncloudos, and the target user's ~/.config / ~/.local/share) rather
  than going through validate_update_target, which would refuse every write here.
"""

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


def _confined(dest, root) -> bool:
    """True only if dest resolves to a location at or under root (blocks .. traversal)."""
    try:
        d = Path(dest).resolve()
        r = Path(root).resolve()
        return d == r or r in d.parents
    except Exception:
        return False


def target_home() -> Path:
    """The home dir to install user-level files into (handles being run under sudo)."""
    import pwd
    if os.geteuid() == 0 and os.environ.get("SUDO_USER"):
        try:
            return Path(pwd.getpwnam(os.environ["SUDO_USER"]).pw_dir)
        except KeyError:
            pass
    return Path.home()


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
        mkdir_result = subprocess.run(['sudo', 'mkdir', '-p', str(dest.parent)],
                                      capture_output=True, timeout=30)
        if mkdir_result.returncode != 0:
            logger.warning(f"sudo mkdir -p {dest.parent} returned {mkdir_result.returncode}")
        cp_result = subprocess.run(['sudo', 'cp', tmp_path, str(dest)],
                                   capture_output=True, timeout=30)
        if cp_result.returncode != 0:
            return False
        chmod_result = subprocess.run(['sudo', 'chmod', oct(mode)[2:], str(dest)],
                                      capture_output=True, timeout=30)
        if chmod_result.returncode != 0:
            logger.warning(f"sudo chmod on {dest} returned {chmod_result.returncode}")
        return True
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
    """Map launcher basename -> /opt destination, parsed from custom .desktop Exec lines.

    Algorithm (applied to each Exec= line):
    1. If the line contains an absolute /opt/.../foo.sh path, use it directly.
    2. Otherwise, locate a working directory from --working-directory[=]"?(/opt/...)
       or cd /opt/... in the command, then combine with a relative ./foo.sh script.
    """
    dest_map: Dict[str, str] = {}
    custom = Path(repo_dir) / "docs" / "configs" / "launchers" / "custom"
    if not custom.is_dir():
        return dest_map

    # Rule 1: bare absolute /opt/…/foo.sh anywhere on the line
    abs_re = re.compile(r"(/opt/[^\s\"';]+\.sh)")

    # Rule 2a: --working-directory="…" or --working-directory=…  (with optional space instead of =)
    wdir_re = re.compile(r'--working-directory[= ]"?(/opt/[^\s"\'&]+)"?')

    # Rule 2b: cd /opt/…  (stop at whitespace, quotes, semicolons, ampersands)
    cd_re = re.compile(r"cd\s+(/opt/[^\s\"';&#]+)")

    # Rule 2c: relative script  ./foo.sh  (optionally preceded by /usr/bin/zsh or similar)
    rel_re = re.compile(r"\./([^\s\"';]+\.sh)")

    for desktop in custom.glob("*.desktop"):
        for line in desktop.read_text(errors="ignore").splitlines():
            if not line.startswith("Exec="):
                continue

            # Rule 1: any absolute /opt/…/.sh takes priority
            abs_matches = abs_re.findall(line)
            if abs_matches:
                for p in abs_matches:
                    dest_map[Path(p).name] = p
                continue

            # Rule 2: working-directory + relative script
            wdir_m = wdir_re.search(line)
            cd_m = cd_re.search(line)
            working_dir = (wdir_m or cd_m)
            if working_dir:
                directory = working_dir.group(1).rstrip("/")
                rel_m = rel_re.search(line)
                if rel_m:
                    fname = rel_m.group(1)
                    dest_map[fname] = f"{directory}/{fname}"

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
            if not _confined(dest, "/opt"):
                logger.warning(f"Refusing launcher destination outside /opt: {dest}")
                continue
            if _write_file(sh.read_bytes(), Path(dest), 0o755):
                placed.append(dest)
    return placed
