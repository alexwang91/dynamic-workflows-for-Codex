from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cdw.plugin_package import PLUGIN_NAME, package_repo_marketplace


@dataclass(frozen=True)
class BootstrapReport:
    marketplace_path: Path
    plugin_path: Path

    def to_text(self) -> str:
        return "\n".join(
            [
                f"marketplace {self.marketplace_path}",
                f"plugin {self.plugin_path}",
                "next codex plugin marketplace add .agents/plugins",
                "doctor python -m cdw doctor",
            ]
        )


def run_bootstrap(root: Path) -> BootstrapReport:
    marketplace_path = package_repo_marketplace(root)
    plugin_path = root / ".agents" / "plugins" / "plugins" / PLUGIN_NAME
    return BootstrapReport(
        marketplace_path=marketplace_path,
        plugin_path=plugin_path,
    )
