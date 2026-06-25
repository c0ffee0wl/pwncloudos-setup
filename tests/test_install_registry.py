from pathlib import Path

from src.tools.registry import get_updater_for_tool
from src.updaters import GitUpdater, GitPythonUpdater, FileReplacementUpdater


def test_install_routes_git_to_gitupdater_even_without_dotgit(tmp_path, config, tool_factory):
    # Fresh install: directory does not exist / has no .git
    tool = tool_factory(install_method="git", path=tmp_path / "missing")
    updater = get_updater_for_tool(tool, config, for_install=True)
    assert isinstance(updater, GitUpdater)


def test_install_routes_git_python_to_gitpython(tmp_path, config, tool_factory):
    tool = tool_factory(install_method="git_python", path=tmp_path / "missing")
    updater = get_updater_for_tool(tool, config, for_install=True)
    assert isinstance(updater, GitPythonUpdater)


def test_update_still_falls_back_to_file_replacement_without_dotgit(tmp_path, config, tool_factory):
    tool = tool_factory(install_method="git", path=tmp_path / "missing")
    updater = get_updater_for_tool(tool, config, for_install=False)
    assert isinstance(updater, FileReplacementUpdater)
