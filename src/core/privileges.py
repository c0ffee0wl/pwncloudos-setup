"""
Privilege management for pwncloudos-sync.
"""

import subprocess
import os
import logging
from typing import List, Optional

logger = logging.getLogger('pwncloudos-sync')


def has_passwordless_sudo() -> bool:
    """
    Check whether sudo can run without prompting for a password.

    Uses the non-interactive flag (``-n``), so this never prompts: it
    succeeds when running as root, with NOPASSWD sudoers rules, or when
    credentials are already cached, and fails fast otherwise.

    Returns:
        bool: True if sudo runs without a password prompt
    """
    if os.geteuid() == 0:
        return True

    try:
        return subprocess.run(
            ['sudo', '-n', 'true'],
            capture_output=True,
            timeout=5
        ).returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_sudo_available() -> bool:
    """
    Check if sudo is available and user has sudo privileges.

    Returns:
        bool: True if sudo is available
    """
    # Already usable without a password (root, NOPASSWD, or cached creds)
    if has_passwordless_sudo():
        return True

    # Otherwise sudo is available only if the user can authenticate
    try:
        result = subprocess.run(
            ['sudo', '-v'],
            capture_output=True,
            timeout=60
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def request_sudo_upfront() -> bool:
    """
    Request sudo password upfront to cache credentials.

    Short-circuits without prompting when sudo is already usable without a
    password (root, NOPASSWD, or cached credentials).

    Returns:
        bool: True if sudo credentials are cached
    """
    if has_passwordless_sudo():
        return True

    logger.info("Requesting sudo privileges...")

    try:
        result = subprocess.run(
            ['sudo', '-v'],
            timeout=120
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error("Sudo prompt timed out")
        return False


def run_as_root(command: List[str], capture_output: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    """
    Execute a command with root privileges.

    Args:
        command: Command to execute as list of strings
        capture_output: Whether to capture stdout/stderr
        timeout: Timeout in seconds (default 300)

    Returns:
        CompletedProcess result
    """
    if os.geteuid() == 0:
        # Already root
        return subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
    else:
        # Use sudo
        return subprocess.run(
            ['sudo'] + command,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )


def get_required_privileges(tool_path: str) -> str:
    """
    Determine what privileges are required for updating a tool.

    Args:
        tool_path: Path to the tool

    Returns:
        str: 'root', 'user', or 'none'
    """
    path = str(tool_path)

    # /opt/ requires root
    if path.startswith('/opt/'):
        return 'root'

    # /usr/ requires root
    if path.startswith('/usr/'):
        return 'root'

    # ~/.local/pipx is user-level
    if '.local/pipx' in path:
        return 'user'

    # Home directory is user-level
    home = os.path.expanduser('~')
    if path.startswith(home):
        return 'user'

    # Default to root for safety
    return 'root'


def can_write_to(path: str) -> bool:
    """
    Check if we can write to a path.

    Args:
        path: Path to check

    Returns:
        bool: True if writable
    """
    return os.access(path, os.W_OK)
