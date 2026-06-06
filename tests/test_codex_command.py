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


def test_resolve_codex_command_skips_windowsapps_package_when_user_cli_exists(
    monkeypatch,
    tmp_path,
):
    user_cli = tmp_path / "OpenAI" / "Codex" / "bin" / "codex.exe"
    user_cli.parent.mkdir(parents=True)
    user_cli.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "shutil.which",
        lambda command: (
            "C:/Program Files/WindowsApps/OpenAI.Codex_1.0.0.0_x64/app/"
            "resources/codex.exe"
        ),
    )

    resolution = resolve_codex_command(env={"LOCALAPPDATA": str(tmp_path)})

    assert resolution.command == str(user_cli)
    assert resolution.source == "path"


def test_resolve_codex_command_reports_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: None)

    resolution = resolve_codex_command(env={})

    assert resolution.command is None
    assert resolution.source == "missing"
