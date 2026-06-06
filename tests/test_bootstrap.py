from cdw.bootstrap import run_bootstrap


def test_bootstrap_prepares_repo_plugin_and_next_steps(tmp_path):
    report = run_bootstrap(tmp_path)

    assert report.marketplace_path == tmp_path / ".agents" / "plugins" / "marketplace.json"
    assert report.plugin_path == (
        tmp_path
        / ".agents"
        / "plugins"
        / "plugins"
        / "dynamic-workflows-for-codex"
    )
    assert report.marketplace_path.exists()
    assert (report.plugin_path / ".codex-plugin" / "plugin.json").exists()

    text = report.to_text()
    assert "marketplace " in text
    assert "plugin " in text
    assert "codex plugin marketplace add .agents/plugins" in text
    assert "python -m cdw doctor" in text
