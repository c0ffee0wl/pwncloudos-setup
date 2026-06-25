import src.updaters.docker_updater as du


def test_docker_install_skips_without_compose(tmp_path, config, tool_factory, monkeypatch):
    tool = tool_factory(
        install_method="docker",
        path=tmp_path / "bloodhound",
        docker_compose=str(tmp_path / "bloodhound" / "bloodhound.yml"),
    )
    updater = du.DockerUpdater(tool, config)
    # Ensure perform_update is NOT called when no compose file exists.
    monkeypatch.setattr(updater, "perform_update",
                        lambda: (_ for _ in ()).throw(AssertionError("should not pull")))

    result = updater.perform_install()
    assert result.skipped is True
    assert "compose" in result.skip_reason.lower()


def test_docker_install_pulls_when_compose_present(tmp_path, config, tool_factory, monkeypatch):
    tool_dir = tmp_path / "bloodhound"
    tool_dir.mkdir(parents=True)
    compose = tool_dir / "bloodhound.yml"
    compose.write_text("services: {}\n")
    tool = tool_factory(install_method="docker", path=tool_dir, docker_compose=str(compose))

    updater = du.DockerUpdater(tool, config)
    sentinel = du.UpdateResult(success=True, tool_name=tool.name, new_version="latest")
    monkeypatch.setattr(updater, "perform_update", lambda: sentinel)

    result = updater.perform_install()
    assert result is sentinel
