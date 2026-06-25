import src.main as main
from src.cli import create_parser


def test_no_configs_and_no_desktop_flags_parse():
    args = create_parser().parse_args(["install", "--no-configs", "--no-desktop"])
    assert args.no_configs is True
    assert args.no_desktop is True


def test_run_configs_phase_invokes_installers(monkeypatch, tmp_path, config):
    calls = []
    monkeypatch.setattr("src.installer.configs.fetch_upstream", lambda: tmp_path / "repo")
    monkeypatch.setattr("src.installer.configs.install_powershell_profiles",
                        lambda repo, **k: calls.append("pwsh") or [])
    monkeypatch.setattr("src.installer.configs.install_launchers",
                        lambda repo: calls.append("launchers") or [])
    monkeypatch.setattr("src.installer.menu.install_icons",
                        lambda repo: calls.append("icons") or 0)
    monkeypatch.setattr("src.installer.menu.install_menu_entries",
                        lambda repo, **k: calls.append("menu") or {})
    monkeypatch.setattr("shutil.rmtree", lambda *a, **k: None)

    config.install_configs = True
    config.install_desktop = True
    config.dry_run = False
    main.run_configs_phase(config, None)
    assert "pwsh" in calls and "launchers" in calls and "menu" in calls


def test_run_configs_phase_respects_no_desktop(monkeypatch, tmp_path, config):
    calls = []
    monkeypatch.setattr("src.installer.configs.fetch_upstream", lambda: tmp_path / "repo")
    monkeypatch.setattr("src.installer.configs.install_powershell_profiles",
                        lambda repo, **k: calls.append("pwsh") or [])
    monkeypatch.setattr("src.installer.configs.install_launchers",
                        lambda repo: calls.append("launchers") or [])
    monkeypatch.setattr("src.installer.menu.install_menu_entries",
                        lambda repo, **k: calls.append("menu") or {})
    monkeypatch.setattr("shutil.rmtree", lambda *a, **k: None)

    config.install_configs = True
    config.install_desktop = False
    config.dry_run = False
    main.run_configs_phase(config, None)
    assert "menu" not in calls
