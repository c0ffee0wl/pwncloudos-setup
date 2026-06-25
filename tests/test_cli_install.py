from pathlib import Path

import src.main as main
from src.cli import create_parser
from src.updaters.base import UpdateResult


def test_parser_accepts_install_command():
    parser = create_parser()
    args = parser.parse_args(["install", "--category", "aws"])
    assert args.command == "install"
    assert args.category == "aws"


def test_run_install_returns_zero_on_success(monkeypatch, config, tool_factory):
    tools = [tool_factory(name="t1"), tool_factory(name="t2")]

    class FakeUpdater:
        def __init__(self, tool):
            self.tool = tool

        def is_installed(self):
            return False

        def perform_install(self):
            return UpdateResult(success=True, tool_name=self.tool.name, new_version="1.0")

        def verify_update(self):
            return True

    monkeypatch.setattr("src.tools.registry.get_updater_for_tool",
                        lambda tool, cfg, for_install=False: FakeUpdater(tool))
    monkeypatch.setattr("src.core.arch.detect_architecture", lambda: "amd64")

    rc = main.run_install(tools, config)
    assert rc == 0


def test_run_install_returns_two_when_all_fail(monkeypatch, config, tool_factory):
    tools = [tool_factory(name="t1")]

    class FailUpdater:
        def __init__(self, tool):
            self.tool = tool

        def is_installed(self):
            return False

        def perform_install(self):
            return UpdateResult(success=False, tool_name=self.tool.name,
                                error_message="boom")

        def verify_update(self):
            return False

    monkeypatch.setattr("src.tools.registry.get_updater_for_tool",
                        lambda tool, cfg, for_install=False: FailUpdater(tool))
    monkeypatch.setattr("src.core.arch.detect_architecture", lambda: "amd64")

    rc = main.run_install(tools, config)
    assert rc == 2


def test_run_install_returns_one_on_partial_failure(monkeypatch, config, tool_factory):
    tools = [tool_factory(name="ok"), tool_factory(name="bad")]

    class PartialUpdater:
        def __init__(self, tool):
            self.tool = tool

        def is_installed(self):
            return False

        def perform_install(self):
            ok = self.tool.name == "ok"
            from src.updaters.base import UpdateResult
            return UpdateResult(success=ok, tool_name=self.tool.name,
                                new_version="1.0" if ok else None,
                                error_message=None if ok else "boom")

        def verify_update(self):
            return True

    monkeypatch.setattr("src.tools.registry.get_updater_for_tool",
                        lambda tool, cfg, for_install=False: PartialUpdater(tool))
    monkeypatch.setattr("src.core.arch.detect_architecture", lambda: "amd64")

    rc = main.run_install(tools, config)
    assert rc == 1
