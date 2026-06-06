import subprocess
from types import SimpleNamespace

from cdw.live_smoke import build_live_smoke_contract, run_live_smoke


def test_live_smoke_reports_missing_codex_without_traceback(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda command: None)

    report = run_live_smoke(tmp_path, execute=False)

    assert not report.ok
    assert any(
        check.name == "codex-command" and not check.ok for check in report.checks
    )
    assert "not found" in report.to_text().lower()


def test_live_smoke_contract_does_not_run_preflight(monkeypatch, tmp_path):
    def fail_find_spec(name):
        raise AssertionError("dry contract must not check imports")

    def fail_run(args, **kwargs):
        raise AssertionError("dry contract must not execute subprocesses")

    monkeypatch.setattr("importlib.util.find_spec", fail_find_spec)
    monkeypatch.setattr("subprocess.run", fail_run)

    contract = build_live_smoke_contract(tmp_path)

    assert contract["tool"] == "codex"
    assert contract["arguments"]["cwd"] == str(tmp_path)
    assert contract["arguments"]["sandbox"] == "workspace-write"
    assert contract["arguments"]["approval-policy"] == "never"
    assert "live worker" in contract["arguments"]["prompt"]


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


def test_live_smoke_execute_uses_resolved_codex_command(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="codex-test 1.0",
            stderr="",
        ),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_execute_plan(plan, root, adapter):
        captured["codex_command"] = adapter.codex_command
        return SimpleNamespace(run_id="live123")

    monkeypatch.setattr("cdw.live_smoke.execute_plan", fake_execute_plan)

    report = run_live_smoke(tmp_path, execute=True, codex_command="codex-test")

    assert report.ok
    assert report.run_id == "live123"
    assert captured["codex_command"] == "codex-test"


def test_live_smoke_execute_reports_runtime_failure(monkeypatch, tmp_path):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="codex-test 1.0",
            stderr="",
        ),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_execute_plan(plan, root, adapter):
        raise RuntimeError("live failed")

    monkeypatch.setattr("cdw.live_smoke.execute_plan", fake_execute_plan)

    report = run_live_smoke(tmp_path, execute=True, codex_command="codex-test")

    assert not report.ok
    assert any(check.name == "live-run" and not check.ok for check in report.checks)
    assert "live failed" in report.to_text()
