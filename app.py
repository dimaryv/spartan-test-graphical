#!/usr/bin/env python3
"""Entry point for the Spartan Test Runner GUI."""

from __future__ import annotations

import tkinter as tk

from spartan_runner.asset_tag import read_asset_tag
from spartan_runner.config_store import load_server_configs
from spartan_runner.theme import configure_theme
from spartan_runner.ui.selection_window import SelectionWindow


def main() -> None:
    root = tk.Tk()
    root.geometry("1280x820")
    root.minsize(1100, 700)
    root.attributes("-fullscreen", True)
    root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False))
    configure_theme(root)
    SelectionWindow(root, load_server_configs(), read_asset_tag())
    root.mainloop()


if __name__ == "__main__":
    main()
