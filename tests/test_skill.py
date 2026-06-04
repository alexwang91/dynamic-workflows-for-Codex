from cdw.skill import install_skill


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
