import json

from cdw.plugin_package import package_plugin, package_repo_marketplace


def test_package_plugin_writes_manifest_and_skill(tmp_path):
    path = package_plugin(tmp_path)

    manifest_path = path / ".codex-plugin" / "plugin.json"
    skill_path = path / "skills" / "dynamic-workflows-for-codex" / "SKILL.md"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    content = skill_path.read_text(encoding="utf-8")

    assert path == tmp_path / "dynamic-workflows-for-codex"
    assert manifest["name"] == "dynamic-workflows-for-codex"
    assert manifest["version"] == "0.6.0"
    assert manifest["skills"] == "./skills/"
    assert "runtime owns orchestration" in content


def test_package_repo_marketplace_writes_marketplace_and_plugin(tmp_path):
    marketplace_path = package_repo_marketplace(tmp_path)

    plugin_path = (
        tmp_path
        / ".agents"
        / "plugins"
        / "plugins"
        / "dynamic-workflows-for-codex"
    )
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))

    assert marketplace_path == tmp_path / ".agents" / "plugins" / "marketplace.json"
    assert marketplace["name"] == "dynamic-workflows-for-codex"
    assert marketplace["plugins"][0]["name"] == "dynamic-workflows-for-codex"
    assert marketplace["plugins"][0]["source"]["path"] == (
        "./plugins/dynamic-workflows-for-codex"
    )
    assert (plugin_path / ".codex-plugin" / "plugin.json").exists()
