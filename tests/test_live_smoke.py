from cdw.live_smoke import run_live_smoke


def test_live_smoke_reports_missing_codex_without_traceback(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda command: None)

    report = run_live_smoke(tmp_path, execute=False)

    assert not report.ok
    assert any(
        check.name == "codex-command" and not check.ok for check in report.checks
    )
    assert "not found" in report.to_text().lower()
