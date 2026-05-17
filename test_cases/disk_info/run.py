#!/usr/bin/env python3
"""Test case that prints disk information."""

import shutil
import subprocess


def main() -> int:
    print("Disk test case started")
    total, used, free = shutil.disk_usage("/")
    gib = 1024 ** 3
    print(f"Root filesystem: total={total / gib:.1f} GiB used={used / gib:.1f} GiB free={free / gib:.1f} GiB")

    print("Mounted block devices:")
    result = subprocess.run(
        ["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINTS"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout.rstrip())
    print("Disk test case finished")
    return 0 if result.returncode == 0 else result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
