"""Fullscreen execution report window."""

from __future__ import annotations

import queue
import subprocess
import threading
import time
import tkinter as tk
from typing import Callable

from spartan_runner.models import TestCase
from spartan_runner.theme import COLORS, LOG_TAG_COLORS, STATUS_STYLES


class RunWindow(tk.Frame):
    def __init__(
        self,
        master: tk.Tk | tk.Toplevel,
        all_cases: list[TestCase],
        selected_cases: list[TestCase],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=COLORS["log_bg"])
        self.master = master
        self.all_cases = all_cases
        self.selected_cases = selected_cases
        self.on_close = on_close
        self.status_by_case = {case: ("pending" if case in selected_cases else "skipped") for case in all_cases}
        self.status_rows: dict[TestCase, tk.Frame] = {}
        self.status_labels: dict[TestCase, tk.Label] = {}
        self.status_spinners: dict[TestCase, tuple[tk.Canvas, int]] = {}
        self.spinner_angle = 0
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.pack(fill=tk.BOTH, expand=True)
        self.build_ui()
        self.master.attributes("-fullscreen", True)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.master.bind("<Escape>", lambda event: self.master.attributes("-fullscreen", False))
        threading.Thread(target=self.worker, daemon=True).start()
        self.process_events()
        self.animate_spinners()

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
        log_scroll = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
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
        spinner = tk.Canvas(row, width=28, height=28, bg=style["bg"], highlightthickness=0)
        spinner_item = spinner.create_arc(5, 5, 23, 23, start=0, extent=270, style=tk.ARC, width=4, outline=COLORS["primary"])
        spinner.itemconfigure(spinner_item, state=(tk.NORMAL if status == "running" else tk.HIDDEN))
        spinner.pack(side=tk.RIGHT, padx=(8, 0))
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
        self.status_spinners[test_case] = (spinner, spinner_item)

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
        spinner, spinner_item = self.status_spinners[test_case]
        spinner.configure(bg=style["bg"])
        spinner.itemconfigure(spinner_item, state=(tk.NORMAL if status == "running" else tk.HIDDEN))
        label.configure(text=self.format_status(status), fg=style["fg"])

    def animate_spinners(self) -> None:
        self.spinner_angle = (self.spinner_angle + 14) % 360
        for test_case, (spinner, spinner_item) in self.status_spinners.items():
            if self.status_by_case[test_case] == "running":
                spinner.itemconfigure(spinner_item, start=self.spinner_angle)
        self.after(80, self.animate_spinners)

    @staticmethod
    def format_status(status: str) -> str:
        style = STATUS_STYLES[status]
        return f"{style['icon']} {status.upper()}"
