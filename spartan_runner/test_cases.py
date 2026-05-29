"""Test case discovery and filtering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from spartan_runner.models import TestCase
from spartan_runner.paths import TEST_CASES_DIR

ALL_CONFIGS = "all"


def load_test_cases(selected_config: str | None = None, test_cases_dir: Path = TEST_CASES_DIR) -> list[TestCase]:
    """Discover test case folders and optionally filter by server config id."""

    test_cases: list[TestCase] = []
    if not test_cases_dir.exists():
        return test_cases

    for child in sorted(path for path in test_cases_dir.iterdir() if path.is_dir()):
        metadata_path = child / "metadata.json"
        runner_path = child / "run.py"
        if not metadata_path.exists() or not runner_path.exists():
            continue

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Skipping {child.name}: cannot read metadata.json: {exc}", file=sys.stderr)
            continue

        configs = metadata.get("configs", [ALL_CONFIGS])
        if not isinstance(configs, list) or not all(isinstance(item, str) for item in configs):
            configs = [ALL_CONFIGS]
        config_tuple = tuple(configs)
        if selected_config and ALL_CONFIGS not in config_tuple and selected_config not in config_tuple:
            continue

        name = str(metadata.get("name") or child.name)
        description = str(metadata.get("description") or "")
        command = metadata.get("command")
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            command_tuple = (sys.executable, str(runner_path))
        else:
            command_tuple = tuple(item.replace("{python}", sys.executable).replace("{case_dir}", str(child)) for item in command)

        test_cases.append(TestCase(name=name, description=description, path=child, command=command_tuple, configs=config_tuple))

    return test_cases
