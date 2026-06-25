from pathlib import Path

from src.updaters.base import BaseUpdater, UpdateResult


class _Dummy(BaseUpdater):
    """Concrete updater for exercising base-class defaults."""

    def get_current_version(self):
        return None

    def get_latest_version(self):
        return None

    def needs_update(self):
        return False

    def perform_update(self):
        return UpdateResult(success=True, tool_name=self.tool.name, new_version="from-update")


def test_is_installed_true_when_path_exists(tmp_path, config, tool_factory):
    p = tmp_path / "thing"
    p.write_text("x")
    updater = _Dummy(tool_factory(path=p), config)
    assert updater.is_installed() is True


def test_is_installed_false_when_absent(tmp_path, config, tool_factory):
    updater = _Dummy(tool_factory(path=tmp_path / "nope", name="zzz-not-a-real-cmd"), config)
    assert updater.is_installed() is False


def test_default_perform_install_delegates_to_update(tmp_path, config, tool_factory):
    updater = _Dummy(tool_factory(path=tmp_path / "nope"), config)
    result = updater.perform_install()
    assert result.success is True
    assert result.new_version == "from-update"
