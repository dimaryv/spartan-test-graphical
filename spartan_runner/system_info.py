"""Linux server characteristic probes."""

from __future__ import annotations

import os
import platform
from pathlib import Path


def bytes_to_gib(value: int) -> str:
    return f"{value / (1024 ** 3):.1f} GiB"


def get_memory_total() -> str:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                kib = int(line.split()[1])
                return bytes_to_gib(kib * 1024)
    except (OSError, ValueError, IndexError):
        pass
    return "Unknown"


def get_cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Unknown"


def get_root_disk_size() -> str:
    try:
        usage = os.statvfs("/")
        total = usage.f_blocks * usage.f_frsize
        free = usage.f_bavail * usage.f_frsize
        return f"{bytes_to_gib(total)} total, {bytes_to_gib(free)} available"
    except OSError:
        return "Unknown"


def get_distribution_name() -> str:
    if not hasattr(platform, "freedesktop_os_release"):
        return "Unknown"
    try:
        return platform.freedesktop_os_release().get("PRETTY_NAME", "Unknown")
    except OSError:
        return "Unknown"


def get_server_characteristics() -> list[tuple[str, str]]:
    uname = platform.uname()
    return [
        ("Hostname", uname.node or "Unknown"),
        ("OS", f"{uname.system} {uname.release}".strip()),
        ("Distribution", get_distribution_name()),
        ("Architecture", platform.machine() or "Unknown"),
        ("CPU", get_cpu_model()),
        ("CPU cores", str(os.cpu_count() or "Unknown")),
        ("Memory", get_memory_total()),
        ("Root disk", get_root_disk_size()),
        ("Python", platform.python_version()),
    ]
