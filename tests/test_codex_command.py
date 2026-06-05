from cdw.codex_command import resolve_codex_command


def test_resolve_codex_command_prefers_explicit_value():
    resolution = resolve_codex_command(
        explicit="C:/tools/codex.exe",
        env={},
    )

    assert resolution.command == "C:/tools/codex.exe"
    assert resolution.source == "cli"


def test_resolve_codex_command_uses_environment(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: None)

    resolution = resolve_codex_command(env={"CDW_CODEX_COMMAND": "D:/codex.exe"})

    assert resolution.command == "D:/codex.exe"
    assert resolution.source == "env"


def test_resolve_codex_command_falls_back_to_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: "C:/bin/codex.exe")

    resolution = resolve_codex_command(env={})

    assert resolution.command == "C:/bin/codex.exe"
    assert resolution.source == "path"


def test_resolve_codex_command_reports_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: None)

    resolution = resolve_codex_command(env={})

    assert resolution.command is None
    assert resolution.source == "missing"
