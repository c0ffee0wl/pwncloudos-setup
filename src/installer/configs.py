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
