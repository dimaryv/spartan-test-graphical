"""Server configuration template loading."""

from __future__ import annotations

import json
from pathlib import Path

from spartan_runner.models import ServerConfig
from spartan_runner.paths import SERVER_CONFIGS_PATH


def load_server_configs(config_path: Path = SERVER_CONFIGS_PATH) -> list[ServerConfig]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    configs: list[ServerConfig] = []
    for item in data.get("configs", []):
        configs.append(
            ServerConfig(
                config_id=str(item["id"]),
                name=str(item["name"]),
                description=str(item.get("description", "")),
                phase=int(item.get("phase", 2)),
                asset_config=str(item.get("asset_config", item["id"])),
                components={key: int(value) for key, value in item.get("components", {}).items()},
            )
        )
    return configs
