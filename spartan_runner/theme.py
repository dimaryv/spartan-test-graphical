"""Tkinter theme constants and helpers."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

COLORS = {
    "app_bg": "#eef2ff",
    "surface": "#ffffff",
    "surface_soft": "#f8fafc",
    "primary": "#2563eb",
    "primary_dark": "#1e3a8a",
    "primary_soft": "#dbeafe",
    "accent": "#38bdf8",
    "success": "#22c55e",
    "text": "#0f172a",
    "muted": "#64748b",
    "border": "#cbd5e1",
    "log_bg": "#0f172a",
    "log_text": "#e2e8f0",
}

STATUS_STYLES = {
    "pending": {"bg": "#e2e8f0", "fg": "#334155", "icon": "●"},
    "running": {"bg": "#dbeafe", "fg": "#1d4ed8", "icon": "▶"},
    "passed": {"bg": "#dcfce7", "fg": "#15803d", "icon": "✓"},
    "failed": {"bg": "#fee2e2", "fg": "#b91c1c", "icon": "✕"},
    "skipped": {"bg": "#fef3c7", "fg": "#92400e", "icon": "–"},
}

LOG_TAG_COLORS = {
    "info": "#bfdbfe",
    "running": "#93c5fd",
    "passed": "#86efac",
    "failed": "#fca5a5",
    "skipped": "#fde68a",
    "error": "#f87171",
}

COMPONENT_LABELS = {
    "cpu": "CPU",
    "sas": "SAS disks",
    "nvme": "NVMe disks",
    "ssd": "SSD",
    "hdd": "HDD",
    "usb": "USB flash drives",
    "memory": "Memory DIMMs",
}


def configure_theme(root: tk.Tk | tk.Toplevel) -> None:
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("App.TFrame", background=COLORS["app_bg"])
    style.configure("Primary.TButton", background=COLORS["primary"], foreground="#ffffff", padding=(14, 8))
    style.map("Primary.TButton", background=[("active", COLORS["primary_dark"])])
    style.configure("Secondary.TButton", padding=(14, 8))


def make_card(parent: tk.Widget, **pack_options: object) -> tk.Frame:
    card = tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1, padx=16, pady=14)
    card.pack(**pack_options)
    return card
