"""FRU Asset Tag integration.

Production servers will use ipmitool to read/write the FRU Asset Tag. Until real
hardware is available this module uses a JSON file stub while keeping the same
state shape that will be written by ipmitool later.
"""

from __future__ import annotations

import json
from pathlib import Path

from spartan_runner.models import AssetTagState
from spartan_runner.paths import ASSET_TAG_STUB_PATH

DEFAULT_ASSET_TAG = AssetTagState(phase=2, config="intel_2s")
IPMITOOL_READ_COMMAND = ("ipmitool", "fru")
IPMITOOL_WRITE_COMMAND_TEMPLATE = ("ipmitool", "fru", "edit", "0", "field", "a", "<json>")


def encode_asset_tag(state: AssetTagState) -> str:
    return json.dumps(state.to_json_dict(), ensure_ascii=False)


def read_asset_tag(stub_path: Path = ASSET_TAG_STUB_PATH) -> AssetTagState:
    if not stub_path.exists():
        write_asset_tag(DEFAULT_ASSET_TAG, stub_path)
        return DEFAULT_ASSET_TAG
    try:
        data = json.loads(stub_path.read_text(encoding="utf-8"))
        return AssetTagState(phase=int(data.get("phase", 2)), config=str(data.get("config", "unknown")))
    except (OSError, json.JSONDecodeError, ValueError):
        return DEFAULT_ASSET_TAG


def write_asset_tag(state: AssetTagState, stub_path: Path = ASSET_TAG_STUB_PATH) -> None:
    stub_path.parent.mkdir(parents=True, exist_ok=True)
    stub_path.write_text(encode_asset_tag(state) + "\n", encoding="utf-8")
