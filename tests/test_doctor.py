import subprocess

from cdw.doctor import run_doctor


def _write_plugin_package(root):
    skill_path = (
        root
        / ".agents"
        / "plugins"
        / "plugins"
        / "dynamic-workflows-for-codex"
        / "skills"
        / "dynamic-workflows-for-codex"
        / "SKILL.md"
    )
    plugin_root = skill_path.parents[2]
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"

    skill_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("# skill", encoding="utf-8")
    manifest_path.write_text("{}", encoding="utf-8")
    marketplace_path.write_text("{}", encoding="utf-8")


def test_doctor_reports_ready_clone(monkeypatch, tmp_path):
    _write_plugin_package(tmp_path)
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[1] == "--version":
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="codex-cli 1.0",
                stderr="",
            )
        if args[1:] == ["login", "status"]:
            return subprocess.CompletedProcess(args, 0, stdout="logged in", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="exec help", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    report = run_doctor(tmp_path, codex_command="codex-test")

    assert report.ok
    assert [check.name for check in report.checks] == [
        "cdw-runtime",
        "cdw-state",
        "codex-command",
        "codex-version",
        "codex-login",
        "codex-exec",
        "plugin-package",
        "skill-package",
    ]
    assert calls == [
        ["codex-test", "--version"],
        ["codex-test", "login", "status"],
        ["codex-test", "exec", "--help"],
    ]
    exec_check = next(check for check in report.checks if check.name == "codex-exec")
    assert exec_check.message == "codex exec help available"


def test_doctor_reports_missing_codex_without_running_subprocess(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr("shutil.which", lambda command: None)

    def fail_run(args, **kwargs):
        raise AssertionError("doctor should not run subprocess without codex")

    monkeypatch.setattr("subprocess.run", fail_run)

    report = run_doctor(tmp_path)

    assert not report.ok
    assert any(check.name == "codex-command" and not check.ok for check in report.checks)
    assert "not found" in report.to_text().lower()


def test_doctor_reports_missing_plugin_package(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="ok",
            stderr="",
        ),
    )

    report = run_doctor(tmp_path, codex_command="codex-test")

    assert not report.ok
    assert any(check.name == "plugin-package" and not check.ok for check in report.checks)
    assert any(check.name == "skill-package" and not check.ok for check in report.checks)
