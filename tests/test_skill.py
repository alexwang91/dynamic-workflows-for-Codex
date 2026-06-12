from cdw.skill import build_skill_content, install_skill


def test_install_skill_writes_repo_skill(tmp_path):
    path = install_skill(tmp_path)

    assert (
        path
        == tmp_path
        / ".agents"
        / "skills"
        / "dynamic-workflows-for-Codex"
        / "SKILL.md"
    )
    content = path.read_text(encoding="utf-8")
    assert "name: dynamic-workflows-for-Codex" in content
    assert "cdw" in content
    assert "runtime owns orchestration" in content


def test_skill_content_routes_dynamic_workflow_tasks():
    content = build_skill_content()

    assert "## Trigger Routing" in content
    assert "## Operating Loop" in content
    assert "## Adapter Policy" in content
    assert "## Status First" in content
    assert "cdw bootstrap --root <repo>" in content
    assert "cdw doctor --root <repo>" in content
    assert "cdw status <run-id>" in content
    assert "--adapter codex-cli" in content
    assert "stage dependencies" in content
    assert "artifact flow" in content
    assert "cdw artifacts <run-id>" in content
    assert "cdw artifact <run-id>" in content
    assert "hydrated" in content
    assert "write-policy boundaries" in content
    assert "Do not ask for or assume the project author's API key" in content
