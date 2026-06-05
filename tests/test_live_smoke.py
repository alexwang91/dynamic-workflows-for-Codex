import subprocess

from cdw.live_smoke import run_live_smoke


def test_live_smoke_reports_missing_codex_without_traceback(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda command: None)

    report = run_live_smoke(tmp_path, execute=False)

    assert not report.ok
    assert any(
        check.name == "codex-command" and not check.ok for check in report.checks
    )
    assert "not found" in report.to_text().lower()


def test_live_smoke_uses_explicit_codex_command(monkeypatch, tmp_path):
    calls = {}

    def fake_run(args, **kwargs):
        calls["args"] = args
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="codex-test 1.0",
            stderr="",
        )

    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr("subprocess.run", fake_run)

    report = run_live_smoke(tmp_path, codex_command="C:/tools/codex.exe")

    assert report.ok
    assert calls["args"][0] == "C:/tools/codex.exe"
    assert "source=cli" in report.to_text()


def test_live_smoke_replaces_invalid_codex_version_output(monkeypatch, tmp_path):
    run_kwargs = {}

    def fake_run(args, **kwargs):
        run_kwargs.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr("subprocess.run", fake_run)

    report = run_live_smoke(tmp_path, codex_command="codex-test")

    assert report.ok
    assert run_kwargs["encoding"] == "utf-8"
    assert run_kwargs["errors"] == "replace"
