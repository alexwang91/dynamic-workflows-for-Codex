import json

from cdw.plugin_package import package_plugin


def test_package_plugin_writes_manifest_and_skill(tmp_path):
    path = package_plugin(tmp_path)

    manifest_path = path / ".codex-plugin" / "plugin.json"
    skill_path = path / "skills" / "dynamic-workflows-for-codex" / "SKILL.md"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    content = skill_path.read_text(encoding="utf-8")

    assert path == tmp_path / "dynamic-workflows-for-codex"
    assert manifest["name"] == "dynamic-workflows-for-codex"
    assert manifest["skills"] == "./skills/"
    assert "runtime owns orchestration" in content
