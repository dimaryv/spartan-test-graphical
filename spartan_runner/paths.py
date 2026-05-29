"""Filesystem paths used by the application."""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIGS_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"
TEST_CASES_DIR = ROOT_DIR / "test_cases"
SERVER_CONFIGS_PATH = CONFIGS_DIR / "server_configs.json"
ASSET_TAG_STUB_PATH = DATA_DIR / "asset_tag_stub.json"
RUNTIME_STATE_PATH = DATA_DIR / "runtime_state.json"
