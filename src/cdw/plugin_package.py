from __future__ import annotations

import json
from pathlib import Path

from cdw.skill import build_skill_content


PLUGIN_NAME = "dynamic-workflows-for-codex"


def package_plugin(output_parent: Path) -> Path:
    plugin_root = output_parent / PLUGIN_NAME
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    skill_path = plugin_root / "skills" / PLUGIN_NAME / "SKILL.md"

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_path.write_text(
        json.dumps(_plugin_manifest(), indent=2) + "\n",
        encoding="utf-8",
    )
    skill_path.write_text(
        build_skill_content(skill_name=PLUGIN_NAME),
        encoding="utf-8",
    )
    return plugin_root


def _plugin_manifest() -> dict:
    return {
        "name": PLUGIN_NAME,
        "version": "0.3.0",
        "description": "External dynamic workflow runtime entrypoint for Codex.",
        "author": {
            "name": "Local developer",
        },
        "skills": "./skills/",
        "keywords": ["codex", "workflow", "agents", "review", "debug"],
        "interface": {
            "displayName": "Dynamic Workflows for Codex",
            "shortDescription": "Run resumable dynamic workflows through cdw.",
            "longDescription": (
                "Packages a Codex skill wrapper that delegates complex review, "
                "debugging, workflow specs, and guarded migrations to the cdw "
                "external runtime."
            ),
            "developerName": "Local developer",
            "category": "Productivity",
            "capabilities": ["Workflow", "Review"],
            "defaultPrompt": [
                "Review this branch with dynamic workflows.",
                "Debug this flaky test with cdw.",
                "Create a guarded migration workflow.",
            ],
        },
    }
