"""Shared data models for Spartan Test Runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TestCase:
    """A discovered, runnable test case folder."""

    name: str
    description: str
    path: Path
    command: tuple[str, ...]
    configs: tuple[str, ...]


@dataclass(frozen=True)
class ServerConfig:
    """A selectable server configuration template."""

    config_id: str
    name: str
    description: str
    phase: int
    asset_config: str
    components: dict[str, int]


@dataclass(frozen=True)
class AssetTagState:
    """State that is written to the FRU Asset Tag in production."""

    phase: int
    config: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)
