"""Fullscreen selection and configuration window."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from spartan_runner.asset_tag import encode_asset_tag, write_asset_tag
from spartan_runner.models import AssetTagState, ServerConfig, TestCase
from spartan_runner.state import write_runtime_state
from spartan_runner.system_info import get_server_characteristics
from spartan_runner.test_cases import load_test_cases
from spartan_runner.theme import COLORS, COMPONENT_LABELS, make_card
from spartan_runner.ui.run_window import RunWindow


class SelectionWindow(ttk.Frame):
    def __init__(
        self,
        master: tk.Tk,
        server_configs: list[ServerConfig],
        asset_tag: AssetTagState,
    ) -> None:
        super().__init__(master)
        self.master = master
        self.server_configs = server_configs
        self.asset_tag = asset_tag
        self.selected_config = tk.StringVar(value=self.initial_config_id())
        self.component_vars: dict[str, tk.IntVar] = {}
        self.selected: dict[TestCase, tk.BooleanVar] = {}
        self.test_cases: list[TestCase] = []
        self.configure(style="App.TFrame")
        self.pack(fill=tk.BOTH, expand=True)
        self.build_ui()
        self.apply_config_selection()

    def initial_config_id(self) -> str:
        for server_config in self.server_configs:
            if server_config.asset_config == self.asset_tag.config:
                return server_config.config_id
        return self.server_configs[0].config_id if self.server_configs else ""

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
            text="Select server configuration, component counts, and runnable test cases",
            bg=COLORS["primary_dark"],
            fg="#bfdbfe",
            font=("TkDefaultFont", 11),
        ).pack(anchor=tk.W, pady=(4, 0))

        content = tk.Frame(self, bg=COLORS["app_bg"], padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(content, bg=COLORS["app_bg"])
        top_row.pack(fill=tk.X, pady=(0, 16))
        self.build_asset_tag_card(top_row)
        self.build_characteristics_card(top_row)

        main_row = tk.Frame(content, bg=COLORS["app_bg"])
        main_row.pack(fill=tk.BOTH, expand=True)
        self.build_configuration_card(main_row)
        self.build_test_cases_card(main_row)

    def build_asset_tag_card(self, parent: tk.Widget) -> None:
        card = make_card(parent, side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        tk.Label(
            card,
            text="FRU Asset Tag (stub)",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            card,
            text="Production will write this JSON through ipmitool fru. Local development uses data/asset_tag_stub.json.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            wraplength=480,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 10))
        self.asset_tag_label = tk.Label(
            card,
            text=encode_asset_tag(self.asset_tag),
            bg=COLORS["primary_soft"],
            fg=COLORS["primary_dark"],
            font=("TkFixedFont", 11, "bold"),
            padx=12,
            pady=8,
        )
        self.asset_tag_label.pack(anchor=tk.W, fill=tk.X)

    def build_characteristics_card(self, parent: tk.Widget) -> None:
        card = make_card(parent, side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        tk.Label(
            card,
            text="Server characteristics",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("TkDefaultFont", 15, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 8))
        for index, (label, value) in enumerate(get_server_characteristics(), start=1):
            row = ((index - 1) // 2) + 1
            column = ((index - 1) % 2) * 2
            tk.Label(card, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("TkDefaultFont", 9, "bold")).grid(row=row, column=column, sticky=tk.W, padx=(0, 8), pady=3)
            tk.Label(card, text=value, bg=COLORS["surface"], fg=COLORS["text"], wraplength=280, justify=tk.LEFT).grid(row=row, column=column + 1, sticky=tk.W, padx=(0, 20), pady=3)
        card.columnconfigure(1, weight=1)
        card.columnconfigure(3, weight=1)

    def build_configuration_card(self, parent: tk.Widget) -> None:
        card = make_card(parent, side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        tk.Label(card, text="Server configuration", bg=COLORS["surface"], fg=COLORS["text"], font=("TkDefaultFont", 18, "bold")).pack(anchor=tk.W)
        tk.Label(card, text="Choose exactly one template, then adjust replaceable components below.", bg=COLORS["surface"], fg=COLORS["muted"]).pack(anchor=tk.W, pady=(2, 12))

        self.config_cards: dict[str, tk.Frame] = {}
        for server_config in self.server_configs:
            self.add_config_option(card, server_config)

        tk.Label(card, text="Replaceable components", bg=COLORS["surface"], fg=COLORS["text"], font=("TkDefaultFont", 14, "bold")).pack(anchor=tk.W, pady=(16, 8))
        self.components_frame = tk.Frame(card, bg=COLORS["surface"])
        self.components_frame.pack(fill=tk.X)

    def add_config_option(self, parent: tk.Widget, server_config: ServerConfig) -> None:
        row = tk.Frame(parent, bg=COLORS["surface_soft"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10)
        row.pack(fill=tk.X, pady=5)
        self.config_cards[server_config.config_id] = row
        tk.Checkbutton(
            row,
            variable=self.selected_config,
            onvalue=server_config.config_id,
            offvalue="",
            command=lambda config_id=server_config.config_id: self.on_config_clicked(config_id),
            bg=COLORS["surface_soft"],
            activebackground=COLORS["primary_soft"],
            selectcolor=COLORS["primary_soft"],
        ).pack(side=tk.LEFT, padx=(0, 10))
        text_frame = tk.Frame(row, bg=COLORS["surface_soft"])
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(text_frame, text=server_config.name, bg=COLORS["surface_soft"], fg=COLORS["text"], font=("TkDefaultFont", 11, "bold")).pack(anchor=tk.W)
        tk.Label(text_frame, text=server_config.description, bg=COLORS["surface_soft"], fg=COLORS["muted"], justify=tk.LEFT).pack(anchor=tk.W)
        tk.Label(row, text=f"phase {server_config.phase}", bg=COLORS["primary_soft"], fg=COLORS["primary_dark"], font=("TkDefaultFont", 9, "bold"), padx=10, pady=4).pack(side=tk.RIGHT)

    def build_test_cases_card(self, parent: tk.Widget) -> None:
        card = make_card(parent, side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        header = tk.Frame(card, bg=COLORS["surface"])
        header.pack(fill=tk.X, pady=(0, 12))
        title_block = tk.Frame(header, bg=COLORS["surface"])
        title_block.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(title_block, text="Test cases", bg=COLORS["surface"], fg=COLORS["text"], font=("TkDefaultFont", 18, "bold")).pack(anchor=tk.W)
        tk.Label(title_block, text="List changes automatically for the selected server configuration.", bg=COLORS["surface"], fg=COLORS["muted"]).pack(anchor=tk.W, pady=(2, 0))
        self.loaded_count_label = tk.Label(header, text="0 loaded", bg=COLORS["primary_soft"], fg=COLORS["primary_dark"], font=("TkDefaultFont", 10, "bold"), padx=14, pady=7)
        self.loaded_count_label.pack(side=tk.RIGHT)

        list_frame = tk.Frame(card, bg=COLORS["surface"])
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        canvas = tk.Canvas(list_frame, bg=COLORS["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.check_frame = tk.Frame(canvas, bg=COLORS["surface"])
        self.check_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.check_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        buttons = tk.Frame(card, bg=COLORS["surface"])
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Select all", style="Secondary.TButton", command=lambda: self.set_all(True)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Deselect all", style="Secondary.TButton", command=lambda: self.set_all(False)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="▶  Run test cases", style="Primary.TButton", command=self.run_selected).pack(side=tk.RIGHT)

    def on_config_clicked(self, config_id: str) -> None:
        if not self.selected_config.get():
            self.selected_config.set(config_id)
        self.apply_config_selection()

    def apply_config_selection(self) -> None:
        server_config = self.current_config()
        if not server_config:
            return
        self.asset_tag = AssetTagState(phase=server_config.phase, config=server_config.asset_config)
        write_asset_tag(self.asset_tag)
        self.asset_tag_label.configure(text=encode_asset_tag(self.asset_tag))
        self.refresh_config_cards()
        self.render_component_inputs(server_config.components)
        self.refresh_test_cases()
        self.persist_selection()

    def refresh_config_cards(self) -> None:
        selected = self.selected_config.get()
        for config_id, row in self.config_cards.items():
            color = COLORS["primary_soft"] if config_id == selected else COLORS["surface_soft"]
            row.configure(bg=color)
            for child in row.winfo_children():
                child.configure(bg=color)
                for grandchild in child.winfo_children():
                    grandchild.configure(bg=color)

    def render_component_inputs(self, components: dict[str, int]) -> None:
        for child in self.components_frame.winfo_children():
            child.destroy()
        self.component_vars = {}
        for index, (key, label) in enumerate(COMPONENT_LABELS.items()):
            row = index // 2
            column = (index % 2) * 2
            tk.Label(self.components_frame, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("TkDefaultFont", 9, "bold")).grid(row=row, column=column, sticky=tk.W, padx=(0, 8), pady=5)
            variable = tk.IntVar(value=int(components.get(key, 0)))
            variable.trace_add("write", lambda *_args: self.persist_selection())
            self.component_vars[key] = variable
            tk.Spinbox(self.components_frame, from_=0, to=128, textvariable=variable, width=5, justify=tk.CENTER).grid(row=row, column=column + 1, sticky=tk.W, padx=(0, 24), pady=5)

    def refresh_test_cases(self) -> None:
        for child in self.check_frame.winfo_children():
            child.destroy()
        self.selected = {}
        config_id = self.selected_config.get()
        self.test_cases = load_test_cases(config_id)
        self.loaded_count_label.configure(text=f"{len(self.test_cases)} loaded")
        if not self.test_cases:
            tk.Label(self.check_frame, text="No test cases found for this configuration", bg=COLORS["surface"], fg=COLORS["muted"]).pack(anchor=tk.W)
            return
        for index, test_case in enumerate(self.test_cases, start=1):
            self.add_test_case_checkbox(test_case, index)

    def add_test_case_checkbox(self, test_case: TestCase, index: int) -> None:
        var = tk.BooleanVar(value=True)
        self.selected[test_case] = var
        row = tk.Frame(self.check_frame, bg=COLORS["surface_soft"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10)
        row.pack(fill=tk.X, pady=6)
        tk.Label(row, text=f"{index:02d}", bg=COLORS["primary"], fg="#ffffff", font=("TkDefaultFont", 10, "bold"), padx=10, pady=6).pack(side=tk.LEFT, padx=(0, 12))
        details = tk.Frame(row, bg=COLORS["surface_soft"])
        details.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Checkbutton(
            details,
            text=test_case.name,
            variable=var,
            bg=COLORS["surface_soft"],
            activebackground=COLORS["primary_soft"],
            fg=COLORS["text"],
            selectcolor=COLORS["primary_soft"],
            anchor=tk.W,
            font=("TkDefaultFont", 11, "bold"),
        ).pack(fill=tk.X, anchor=tk.W)
        if test_case.description:
            tk.Label(details, text=test_case.description, bg=COLORS["surface_soft"], fg=COLORS["muted"], anchor=tk.W, justify=tk.LEFT).pack(fill=tk.X, anchor=tk.W, padx=(24, 0), pady=(2, 0))
        tk.Label(row, text="Ready", bg=COLORS["primary_soft"], fg=COLORS["primary_dark"], font=("TkDefaultFont", 9, "bold"), padx=10, pady=4).pack(side=tk.RIGHT, padx=(12, 0))

    def set_all(self, value: bool) -> None:
        for variable in self.selected.values():
            variable.set(value)

    def run_selected(self) -> None:
        selected_cases = [test_case for test_case, variable in self.selected.items() if variable.get()]
        if not selected_cases:
            messagebox.showwarning("No test cases selected", "Select at least one test case to run.")
            return
        self.persist_selection()
        run_window = tk.Toplevel(self.master)
        run_window.protocol("WM_DELETE_WINDOW", self.master.destroy)
        self.master.withdraw()
        RunWindow(run_window, self.test_cases, selected_cases, on_close=self.master.destroy)

    def current_config(self) -> ServerConfig | None:
        selected = self.selected_config.get()
        return next((server_config for server_config in self.server_configs if server_config.config_id == selected), None)

    def current_components(self) -> dict[str, int]:
        components: dict[str, int] = {}
        for key, variable in self.component_vars.items():
            try:
                components[key] = int(variable.get())
            except tk.TclError:
                components[key] = 0
        return components

    def persist_selection(self) -> None:
        server_config = self.current_config()
        if not server_config:
            return
        write_runtime_state(server_config, self.current_components(), self.asset_tag)
