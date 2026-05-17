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


@dataclass(frozen=True)
class TestCase:
    """A discovered, runnable test case folder."""

    name: str
    description: str
    path: Path
    command: tuple[str, ...]


def read_first_line(path: Path, default: str = "Unknown") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
    except (OSError, IndexError):
        return default


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


class SelectionWindow(ttk.Frame):
    def __init__(self, master: tk.Tk, test_cases: list[TestCase]) -> None:
        super().__init__(master, padding=16)
        self.master = master
        self.test_cases = test_cases
        self.selected: dict[TestCase, tk.BooleanVar] = {}
        self.pack(fill=tk.BOTH, expand=True)
        self.build_ui()

    def build_ui(self) -> None:
        self.master.title("Spartan Test Runner")
        ttk.Label(self, text="Server characteristics", font=("TkDefaultFont", 16, "bold")).pack(anchor=tk.W)

        characteristics = ttk.Frame(self)
        characteristics.pack(fill=tk.X, pady=(8, 18))
        for row, (label, value) in enumerate(get_server_characteristics()):
            ttk.Label(characteristics, text=f"{label}:", font=("TkDefaultFont", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=(0, 12), pady=2)
            ttk.Label(characteristics, text=value).grid(row=row, column=1, sticky=tk.W, pady=2)
        characteristics.columnconfigure(1, weight=1)

        ttk.Label(self, text="Test cases", font=("TkDefaultFont", 16, "bold")).pack(anchor=tk.W)
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 12))

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.check_frame = ttk.Frame(canvas)
        self.check_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.check_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.test_cases:
            ttk.Label(self.check_frame, text="No test cases found in ./test_cases").pack(anchor=tk.W)
        for test_case in self.test_cases:
            var = tk.BooleanVar(value=True)
            self.selected[test_case] = var
            text = test_case.name if not test_case.description else f"{test_case.name} — {test_case.description}"
            ttk.Checkbutton(self.check_frame, text=text, variable=var).pack(anchor=tk.W, pady=3)

        buttons = ttk.Frame(self)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Select all", command=lambda: self.set_all(True)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Deselect all", command=lambda: self.set_all(False)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Run test cases", command=self.run_selected).pack(side=tk.RIGHT)

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
        super().__init__(master, padding=10)
        self.master = master
        self.all_cases = all_cases
        self.selected_cases = selected_cases
        self.on_close = on_close
        self.status_by_case = {case: ("pending" if case in selected_cases else "skipped") for case in all_cases}
        self.status_labels: dict[TestCase, ttk.Label] = {}
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
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        log_frame = ttk.LabelFrame(paned, text="Execution logs", padding=8)
        status_frame = ttk.LabelFrame(paned, text="Test case statuses", padding=8)
        paned.add(log_frame, weight=1)
        paned.add(status_frame, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, bg="#111827", fg="#e5e7eb", insertbackground="#e5e7eb")
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for row, test_case in enumerate(self.all_cases):
            ttk.Label(status_frame, text=test_case.name).grid(row=row, column=0, sticky=tk.W, padx=(0, 20), pady=5)
            label = ttk.Label(status_frame, text=self.status_by_case[test_case].upper())
            label.grid(row=row, column=1, sticky=tk.W, pady=5)
            self.status_labels[test_case] = label
        status_frame.columnconfigure(0, weight=1)

    def worker(self) -> None:
        self.events.put(("log", "Starting selected test cases...\n"))
        selected_set = set(self.selected_cases)
        for test_case in self.all_cases:
            if test_case not in selected_set:
                self.events.put(("status", (test_case, "skipped")))
                self.events.put(("log", f"[{test_case.name}] skipped\n"))
                continue
            self.events.put(("status", (test_case, "running")))
            self.events.put(("log", f"\n[{test_case.name}] running: {' '.join(test_case.command)}\n"))
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
                    self.events.put(("log", f"[{test_case.name}] {line}"))
                return_code = process.wait()
            except Exception as exc:  # subprocess/runtime error belongs in the UI log
                self.events.put(("log", f"[{test_case.name}] ERROR: {exc}\n"))
                return_code = 1

            elapsed = time.monotonic() - start
            status = "passed" if return_code == 0 else "failed"
            self.events.put(("status", (test_case, status)))
            self.events.put(("log", f"[{test_case.name}] {status.upper()} in {elapsed:.1f}s (exit code {return_code})\n"))
        self.events.put(("log", "\nAll test cases finished. Press Esc to leave fullscreen mode.\n"))
        self.events.put(("done", None))

    def process_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "log":
                    self.append_log(str(payload))
                elif event == "status":
                    test_case, status = payload  # type: ignore[misc]
                    self.update_status(test_case, status)
        except queue.Empty:
            pass
        self.after(100, self.process_events)

    def append_log(self, text: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def update_status(self, test_case: TestCase, status: str) -> None:
        self.status_by_case[test_case] = status
        label = self.status_labels[test_case]
        label.configure(text=status.upper())


def main() -> None:
    root = tk.Tk()
    root.geometry("1000x700")
    root.minsize(800, 500)
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    SelectionWindow(root, load_test_cases())
    root.mainloop()


if __name__ == "__main__":
    main()
