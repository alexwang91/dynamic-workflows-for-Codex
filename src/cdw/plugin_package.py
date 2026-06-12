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


def package_repo_marketplace(root: Path) -> Path:
    marketplace_root = root / ".agents" / "plugins"
    plugin_root = package_plugin(marketplace_root / "plugins")
    marketplace_path = marketplace_root / "marketplace.json"
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace_path.write_text(
        json.dumps(_marketplace_manifest(plugin_root.name), indent=2) + "\n",
        encoding="utf-8",
    )
    return marketplace_path


def _plugin_manifest() -> dict:
    return {
        "name": PLUGIN_NAME,
        "version": "0.14.0",
        "description": "Dynamic workflow runtime with Codex CLI planning, run status inspection, human approval gates, stage dependencies, persisted artifacts, artifact flow, bootstrap, doctor checks, and skill routing.",
        "author": {
            "name": "Local developer",
        },
        "skills": "./skills/",
        "keywords": ["codex", "workflow", "agents", "review", "debug", "doctor"],
        "interface": {
            "displayName": "Dynamic Workflows for Codex",
            "shortDescription": "Bootstrap and route Codex dynamic workflows.",
            "longDescription": (
                "Packages a Codex skill wrapper that bootstraps the repo-local "
                "plugin marketplace, runs cdw doctor readiness checks, routes "
                "dynamic planning and real workers through the user's codex-cli "
                "login, exposes run status inspection for resumable workflows, "
                "enforces human approval gates for guarded stages, and delegates "
                "review, debugging, workflow specs, staged runs, resume, and "
                "guarded migrations to the cdw external runtime. Workflow specs "
                "can express stage dependencies, consumed and produced artifacts, "
                "and stricter write-policy boundaries for write-heavy work. "
                "Verified stage artifacts are persisted under .cdw runs and "
                "hydrated into dependent stage prompts."
            ),
            "developerName": "Local developer",
            "category": "Productivity",
            "capabilities": ["Workflow", "Review"],
            "defaultPrompt": [
                "Bootstrap this clone for Codex dynamic workflows.",
                "Run cdw doctor for this clone.",
                "Create a dynamic workflow spec with Codex CLI.",
                "Inspect workflow spec stage dependencies and artifacts.",
                "List and read persisted workflow artifacts.",
                "Inspect recent workflow run status.",
                "Resume a workflow after human approval.",
                "Review this branch with dynamic workflows.",
                "Debug this flaky test with cdw.",
                "Create and run a reusable workflow spec.",
                "Create a guarded migration workflow.",
            ],
        },
    }


def _marketplace_manifest(plugin_name: str) -> dict:
    return {
        "name": "dynamic-workflows-for-codex",
        "interface": {
            "displayName": "Dynamic Workflows for Codex",
        },
        "plugins": [
            {
                "name": plugin_name,
                "source": {
                    "source": "local",
                    "path": f"./plugins/{plugin_name}",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Productivity",
            }
        ],
    }
