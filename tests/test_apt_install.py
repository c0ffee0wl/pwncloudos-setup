import src.updaters.apt_updater as au
from conftest import FakeCompleted


def test_apt_install_runs_plain_install(config, tool_factory, monkeypatch):
    calls = []
    monkeypatch.setattr(au.subprocess, "run",
                        lambda cmd, *a, **k: calls.append(cmd) or FakeCompleted(0))

    tool = tool_factory(install_method="apt", apt_package="hashcat", path="/usr/bin/hashcat")
    updater = au.AptUpdater(tool, config)
    # Not yet installed, then installed afterwards.
    versions = iter([None, "6.2.6"])
    monkeypatch.setattr(updater, "get_current_version", lambda: next(versions))

    result = updater.perform_install()

    assert result.success is True
    install_cmd = next(c for c in calls if "install" in c)
    assert install_cmd == ["sudo", "apt-get", "install", "-y", "hashcat"]
    assert "--only-upgrade" not in install_cmd


def test_apt_install_skips_when_present(config, tool_factory, monkeypatch):
    tool = tool_factory(install_method="apt", apt_package="hashcat", path="/usr/bin/hashcat")
    updater = au.AptUpdater(tool, config)
    monkeypatch.setattr(updater, "get_current_version", lambda: "6.2.6")
    result = updater.perform_install()
    assert result.skipped is True
