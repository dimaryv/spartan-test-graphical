#!/usr/bin/env python3
"""Test case that prints CPU information."""

from pathlib import Path
import os
import platform


def main() -> int:
    print("CPU test case started")
    print(f"Architecture: {platform.machine()}")
    print(f"Logical cores: {os.cpu_count() or 'Unknown'}")

    model = "Unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except OSError as exc:
        print(f"Could not read /proc/cpuinfo: {exc}")

    print(f"CPU model: {model}")
    print("CPU test case finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
