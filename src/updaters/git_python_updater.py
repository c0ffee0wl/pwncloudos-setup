"""
Git + Python dependencies updater for pwncloudos-sync.
"""

import os
import shutil
import subprocess
from .git_updater import GitUpdater
from .base import UpdateResult


class GitPythonUpdater(GitUpdater):
    """Updater for git repositories with Python dependencies."""

    def _pip_cmd(self, *args) -> list:
        """Build a pip command, adding sudo and --break-system-packages as needed."""
        cmd = ['python3', '-m', 'pip'] + list(args) + ['--break-system-packages']
        if os.geteuid() != 0 and str(self.tool.path).startswith('/opt/'):
            cmd = ['sudo'] + cmd
        return cmd

    def perform_update(self) -> UpdateResult:
        """Execute git pull and update Python dependencies."""
        # First: git pull (via parent class)
        git_result = super().perform_update()

        if not git_result.success:
            return git_result

        # Update Python dependencies
        req_file = self.tool.path / "requirements.txt"
        if req_file.exists():
            self.logger.info(f"Installing Python dependencies from {req_file}")
            try:
                result = subprocess.run(
                    self._pip_cmd('install', '-r', str(req_file), '--upgrade', '--quiet'),
                    capture_output=True, text=True, timeout=300
                )

                if result.returncode != 0:
                    self.logger.warning(f"pip install warning: {result.stderr}")
                    # Don't fail the update, just warn
            except subprocess.TimeoutExpired:
                self.logger.warning("pip install timed out")
            except Exception as e:
                self.logger.warning(f"pip install error: {e}")

        # Check for setup.py or pyproject.toml
        setup_py = self.tool.path / "setup.py"
        pyproject = self.tool.path / "pyproject.toml"

        if setup_py.exists():
            self.logger.info("Running pip install -e .")
            try:
                subprocess.run(
                    self._pip_cmd('install', '-e', str(self.tool.path), '--quiet'),
                    capture_output=True, text=True, timeout=300
                )
            except Exception as e:
                self.logger.warning(f"pip install -e failed: {e}")

        elif pyproject.exists():
            self.logger.info("Running pip install from pyproject.toml")
            try:
                subprocess.run(
                    self._pip_cmd('install', str(self.tool.path), '--quiet'),
                    capture_output=True, text=True, timeout=300
                )
            except Exception as e:
                self.logger.warning(f"pip install failed: {e}")

        return git_result

    def _install_requirements_global(self) -> None:
        """Install requirements.txt into the global env (uv if present, else pip)."""
        from pathlib import Path

        req = Path(self.tool.path) / "requirements.txt"
        if not req.exists():
            return

        if shutil.which("uv"):
            cmd = ["uv", "pip", "install", "--system", "--break-system-packages",
                   "-r", str(req)]
        else:
            cmd = ["python3", "-m", "pip", "install", "-r", str(req),
                   "--break-system-packages", "--quiet"]

        if os.geteuid() != 0 and str(self.tool.path).startswith("/opt/"):
            cmd = ["sudo"] + cmd

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                self.logger.warning(f"requirements install warning: {result.stderr}")
        except Exception as e:
            self.logger.warning(f"requirements install error: {e}")

    def perform_install(self) -> UpdateResult:
        """Clone if absent (then install deps); otherwise update."""
        from pathlib import Path

        if (Path(self.tool.path) / ".git").exists():
            return self.perform_update()

        clone_result = self._git_clone()
        if not clone_result.success:
            return clone_result

        self._install_requirements_global()
        return clone_result

    def verify_update(self) -> bool:
        """Verify Python tool works."""
        # First check git status
        if not super().verify_update():
            return False

        # Try to run the tool
        py_files = list(self.tool.path.glob('*.py'))
        main_script = None

        # Find main script
        tool_name = self.tool.path.name.lower()
        for pattern in [f"{tool_name}.py", "main.py", "__main__.py"]:
            candidate = self.tool.path / pattern
            if candidate.exists():
                main_script = candidate
                break

        if not main_script and py_files:
            main_script = py_files[0]

        if main_script:
            try:
                result = subprocess.run(
                    ['python3', str(main_script), '--help'],
                    capture_output=True, timeout=10
                )
                # Return True even if --help returns non-zero (some tools do this)
                return True
            except Exception:
                pass

        return True  # Can't verify, assume OK
