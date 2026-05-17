#!/usr/bin/env python3
"""Graphical runner for server test cases on Ubuntu/Linux."""

from __future__ import annotations

import json
import os
import platform
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import messagebox, ttk


ROOT_DIR = Path(__file__).resolve().parent
TEST_CASES_DIR = ROOT_DIR / "test_cases"
STATUSES = ("pending", "running", "passed", "failed", "skipped")

COLORS = {
    "app_bg": "#eef2ff",
    "surface": "#ffffff",
    "surface_soft": "#f8fafc",
    "primary": "#2563eb",
    "primary_dark": "#1e3a8a",
    "primary_soft": "#dbeafe",
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


@dataclass(frozen=True)
class TestCase:
    """A discovered, runnable test case folder."""

    name: str
    description: str
    path: Path
    command: tuple[str, ...]


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


def load_test_cases(test_cases_dir: Path = TEST_CASES_DIR) -> list[TestCase]:
    """Discover test case folders that contain metadata.json and run.py."""

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

        name = str(metadata.get("name") or child.name)
        description = str(metadata.get("description") or "")
        command = metadata.get("command")
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            command = (sys.executable, str(runner_path))
        else:
            command = tuple(item.replace("{python}", sys.executable).replace("{case_dir}", str(child)) for item in command)

        test_cases.append(TestCase(name=name, description=description, path=child, command=command))

    return test_cases


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


class SelectionWindow(ttk.Frame):
    def __init__(self, master: tk.Tk, test_cases: list[TestCase]) -> None:
        super().__init__(master)
        self.master = master
        self.test_cases = test_cases
        self.selected: dict[TestCase, tk.BooleanVar] = {}
        self.configure(style="App.TFrame")
        self.pack(fill=tk.BOTH, expand=True)
        self.build_ui()

    def build_ui(self) -> None:
        self.master.title("Spartan Test Runner")
        self.master.configure(bg=COLORS["app_bg"])

        header = tk.Frame(self, bg=COLORS["primary_dark"], padx=24, pady=18)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="Spartan Test Runner",
            bg=COLORS["primary_dark"],
            fg="#ffffff",
            font=("TkDefaultFont", 24, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text="Select server test cases and monitor execution in a color-coded report",
            bg=COLORS["primary_dark"],
            fg="#bfdbfe",
            font=("TkDefaultFont", 11),
        ).pack(anchor=tk.W, pady=(4, 0))

        content = tk.Frame(self, bg=COLORS["app_bg"], padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        characteristics_card = make_card(content, fill=tk.X, pady=(0, 16))
        tk.Label(
            characteristics_card,
            text="Server characteristics",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))

        for index, (label, value) in enumerate(get_server_characteristics(), start=1):
            row = ((index - 1) // 2) + 1
            column = ((index - 1) % 2) * 2
            tk.Label(
                characteristics_card,
                text=f"{label}",
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("TkDefaultFont", 9, "bold"),
            ).grid(row=row, column=column, sticky=tk.W, padx=(0, 8), pady=4)
            tk.Label(
                characteristics_card,
                text=value,
                bg=COLORS["surface"],
                fg=COLORS["text"],
                wraplength=360,
                justify=tk.LEFT,
            ).grid(row=row, column=column + 1, sticky=tk.W, padx=(0, 24), pady=4)
        characteristics_card.columnconfigure(1, weight=1)
        characteristics_card.columnconfigure(3, weight=1)

        tests_card = make_card(content, fill=tk.BOTH, expand=True)
        tk.Label(
            tests_card,
            text="Test cases",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            tests_card,
            text="All test cases are selected by default.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
        ).pack(anchor=tk.W, pady=(2, 10))

        list_frame = tk.Frame(tests_card, bg=COLORS["surface"])
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        canvas = tk.Canvas(list_frame, bg=COLORS["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.check_frame = tk.Frame(canvas, bg=COLORS["surface"])
        self.check_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.check_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.test_cases:
            tk.Label(
                self.check_frame,
                text="No test cases found in ./test_cases",
                bg=COLORS["surface"],
                fg=COLORS["muted"],
            ).pack(anchor=tk.W)
        for test_case in self.test_cases:
            self.add_test_case_checkbox(test_case)

        buttons = tk.Frame(tests_card, bg=COLORS["surface"])
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Select all", style="Secondary.TButton", command=lambda: self.set_all(True)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Deselect all", style="Secondary.TButton", command=lambda: self.set_all(False)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Run test cases", style="Primary.TButton", command=self.run_selected).pack(side=tk.RIGHT)

    def add_test_case_checkbox(self, test_case: TestCase) -> None:
        var = tk.BooleanVar(value=True)
        self.selected[test_case] = var
        row = tk.Frame(self.check_frame, bg=COLORS["surface_soft"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=8)
        row.pack(fill=tk.X, pady=4)
        text = test_case.name if not test_case.description else f"{test_case.name} — {test_case.description}"
        tk.Checkbutton(
            row,
            text=text,
            variable=var,
            bg=COLORS["surface_soft"],
            activebackground=COLORS["primary_soft"],
            fg=COLORS["text"],
            selectcolor=COLORS["primary_soft"],
            anchor=tk.W,
            font=("TkDefaultFont", 10, "bold"),
        ).pack(fill=tk.X, anchor=tk.W)

    def set_all(self, value: bool) -> None:
        for variable in self.selected.values():
            variable.set(value)

    def run_selected(self) -> None:
        selected_cases = [test_case for test_case, variable in self.selected.items() if variable.get()]
        if not selected_cases:
            messagebox.showwarning("No test cases selected", "Select at least one test case to run.")
            return
        run_window = tk.Toplevel(self.master)
        run_window.protocol("WM_DELETE_WINDOW", self.master.destroy)
        self.master.withdraw()
        RunWindow(run_window, self.test_cases, selected_cases, on_close=self.master.destroy)


class RunWindow(ttk.Frame):
    def __init__(
        self,
        master: tk.Tk | tk.Toplevel,
        all_cases: list[TestCase],
        selected_cases: list[TestCase],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.master = master
        self.all_cases = all_cases
        self.selected_cases = selected_cases
        self.on_close = on_close
        self.status_by_case = {case: ("pending" if case in selected_cases else "skipped") for case in all_cases}
        self.status_rows: dict[TestCase, tk.Frame] = {}
        self.status_labels: dict[TestCase, tk.Label] = {}
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.pack(fill=tk.BOTH, expand=True)
        self.build_ui()
        self.master.attributes("-fullscreen", True)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.master.bind("<Escape>", lambda event: self.master.attributes("-fullscreen", False))
        threading.Thread(target=self.worker, daemon=True).start()
        self.process_events()

    def build_ui(self) -> None:
        self.master.title("Spartan Test Runner — Running")
        self.master.configure(bg=COLORS["log_bg"])
        shell = tk.Frame(self, bg=COLORS["log_bg"], padx=14, pady=14)
        shell.pack(fill=tk.BOTH, expand=True)

        title_bar = tk.Frame(shell, bg=COLORS["log_bg"])
        title_bar.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            title_bar,
            text="Execution report",
            bg=COLORS["log_bg"],
            fg="#ffffff",
            font=("TkDefaultFont", 22, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            title_bar,
            text="Press Esc to leave fullscreen",
            bg=COLORS["log_bg"],
            fg="#94a3b8",
        ).pack(side=tk.RIGHT)

        body = tk.PanedWindow(shell, orient=tk.HORIZONTAL, sashwidth=8, bg=COLORS["log_bg"], bd=0)
        body.pack(fill=tk.BOTH, expand=True)

        log_frame = tk.Frame(body, bg="#111827", highlightbackground="#334155", highlightthickness=1, padx=10, pady=10)
        status_frame = tk.Frame(body, bg=COLORS["surface"], highlightbackground="#334155", highlightthickness=1, padx=12, pady=12)
        body.add(log_frame, stretch="always", minsize=400)
        body.add(status_frame, stretch="always", minsize=400)

        tk.Label(
            log_frame,
            text="Live logs",
            bg="#111827",
            fg="#ffffff",
            font=("TkDefaultFont", 14, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))
        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=COLORS["log_bg"],
            fg=COLORS["log_text"],
            insertbackground=COLORS["log_text"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
            font=("TkFixedFont", 10),
        )
        for tag, color in LOG_TAG_COLORS.items():
            self.log_text.tag_configure(tag, foreground=color)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(
            status_frame,
            text="Test case statuses",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("TkDefaultFont", 14, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            status_frame,
            text="Color-coded execution report",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
        ).pack(anchor=tk.W, pady=(2, 10))

        for test_case in self.all_cases:
            self.add_status_row(status_frame, test_case)

    def add_status_row(self, parent: tk.Widget, test_case: TestCase) -> None:
        status = self.status_by_case[test_case]
        style = STATUS_STYLES[status]
        row = tk.Frame(parent, bg=style["bg"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10)
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text=test_case.name,
            bg=style["bg"],
            fg=COLORS["text"],
            font=("TkDefaultFont", 11, "bold"),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, anchor=tk.W)
        label = tk.Label(
            row,
            text=self.format_status(status),
            bg=style["bg"],
            fg=style["fg"],
            font=("TkDefaultFont", 10, "bold"),
            padx=10,
            pady=4,
        )
        label.pack(side=tk.RIGHT)
        self.status_rows[test_case] = row
        self.status_labels[test_case] = label

    def worker(self) -> None:
        self.events.put(("log", ("Starting selected test cases...\n", "info")))
        selected_set = set(self.selected_cases)
        for test_case in self.all_cases:
            if test_case not in selected_set:
                self.events.put(("status", (test_case, "skipped")))
                self.events.put(("log", (f"[{test_case.name}] skipped\n", "skipped")))
                continue
            self.events.put(("status", (test_case, "running")))
            self.events.put(("log", (f"\n[{test_case.name}] running: {' '.join(test_case.command)}\n", "running")))
            start = time.monotonic()
            try:
                process = subprocess.Popen(
                    test_case.command,
                    cwd=test_case.path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    self.events.put(("log", (f"[{test_case.name}] {line}", "info")))
                return_code = process.wait()
            except Exception as exc:  # subprocess/runtime error belongs in the UI log
                self.events.put(("log", (f"[{test_case.name}] ERROR: {exc}\n", "error")))
                return_code = 1

            elapsed = time.monotonic() - start
            status = "passed" if return_code == 0 else "failed"
            self.events.put(("status", (test_case, status)))
            self.events.put(("log", (f"[{test_case.name}] {status.upper()} in {elapsed:.1f}s (exit code {return_code})\n", status)))
        self.events.put(("log", ("\nAll test cases finished. Press Esc to leave fullscreen mode.\n", "info")))
        self.events.put(("done", None))

    def process_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "log":
                    text, tag = payload  # type: ignore[misc]
                    self.append_log(str(text), str(tag))
                elif event == "status":
                    test_case, status = payload  # type: ignore[misc]
                    self.update_status(test_case, status)
        except queue.Empty:
            pass
        self.after(100, self.process_events)

    def append_log(self, text: str, tag: str = "info") -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text, tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def update_status(self, test_case: TestCase, status: str) -> None:
        self.status_by_case[test_case] = status
        style = STATUS_STYLES[status]
        row = self.status_rows[test_case]
        label = self.status_labels[test_case]
        row.configure(bg=style["bg"])
        for child in row.winfo_children():
            child.configure(bg=style["bg"])
        label.configure(text=self.format_status(status), fg=style["fg"])

    @staticmethod
    def format_status(status: str) -> str:
        style = STATUS_STYLES[status]
        return f"{style['icon']} {status.upper()}"


def main() -> None:
    root = tk.Tk()
    root.geometry("1100x760")
    root.minsize(900, 600)
    configure_theme(root)
    SelectionWindow(root, load_test_cases())
    root.mainloop()


if __name__ == "__main__":
    main()
