"""Runtime state persistence for selected configuration and components."""

from __future__ import annotations

import json
from pathlib import Path

from spartan_runner.asset_tag import encode_asset_tag
from spartan_runner.models import AssetTagState, ServerConfig
from spartan_runner.paths import RUNTIME_STATE_PATH


def write_runtime_state(
    server_config: ServerConfig,
    components: dict[str, int],
    asset_tag: AssetTagState,
    state_path: Path = RUNTIME_STATE_PATH,
) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "asset_tag": asset_tag.to_json_dict(),
        "asset_tag_json": encode_asset_tag(asset_tag),
        "server_config": {
            "id": server_config.config_id,
            "name": server_config.name,
            "phase": server_config.phase,
            "asset_config": server_config.asset_config,
        },
        "components": components,
    }
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
