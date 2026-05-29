#!/usr/bin/env python3
"""Test case that waits for 20 seconds so the UI running animation is visible."""

import time


def main() -> int:
    print("Sleep test case started")
    for second in range(1, 21):
        print(f"Waiting... {second}/20")
        time.sleep(1)
    print("Sleep test case finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
