# app/ui_operator.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from .ui_common import HeaderFrame
from .storage import safe_int, safe_float
from .services.tool_life_service import (
    create_shift_report,
    list_cells,
    list_downtime_codes_service,
    list_lines_service,
    list_machines,
    list_parts,
)
from .ui_error_handling import wrap_ui_action


class OperatorUI(tk.Frame):
    """Operator entry screen for cell/parts and downtime capture."""

    def __init__(self, parent, controller, show_header=True):
        super().__init__(parent, bg=controller.colors["bg"])
        self.controller = controller

        if show_header:
            HeaderFrame(self, controller).pack(fill="x")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        tab_operator = tk.Frame(nb, bg=controller.colors["bg"])
        tab_shift = tk.Frame(nb, bg=controller.colors["bg"])
        nb.add(tab_operator, text="Operator Entry")
        nb.add(tab_shift, text="Shift Production")

        self._build_operator_entry(tab_operator)
        self._build_shift_production(tab_shift)

    def _build_operator_entry(self, parent):
        body = tk.Frame(parent, bg=self.controller.colors["bg"], padx=20, pady=20)
        body.pack(fill="both", expand=True)

        style = {"bg": self.controller.colors["bg"], "fg": self.controller.colors["fg"]}

    def _build_shift_production(self, parent):
        body = tk.Frame(parent, bg=self.controller.colors["bg"], padx=20, pady=20)
        body.pack(fill="both", expand=True)

        style = {"bg": self.controller.colors["bg"], "fg": self.controller.colors["fg"]}

        tk.Label(body, text="Shift Production", font=("Arial", 16, "bold"), **style).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 15)
        )

        tk.Label(body, text="Line:", **style).grid(row=1, column=0, sticky="e", pady=6)
        line_options = list_lines_service()
        if not line_options:
            line_options = ["U725", "JL"]
        self.shift_line_var = tk.StringVar(value=self.controller.user_line or line_options[0])
        self.shift_line_cb = ttk.Combobox(body, values=line_options, state="readonly", width=18)
        if self.shift_line_var.get() in line_options:
            self.shift_line_cb.set(self.shift_line_var.get())
        else:
            self.shift_line_cb.current(0)
        self.shift_line_cb.grid(row=1, column=1, sticky="w")
        self.shift_line_cb.bind("<<ComboboxSelected>>", self._refresh_line_dependent_fields)

        tk.Label(body, text="Shift:", **style).grid(row=1, column=2, sticky="e", pady=6)
        self.shift_var = tk.StringVar(value="1st")
        self.shift_cb = ttk.Combobox(body, values=["1st", "2nd", "3rd"], state="readonly", width=18)
        self.shift_cb.set(self.shift_var.get())
        self.shift_cb.grid(row=1, column=3, sticky="w")

        tk.Label(body, text="Cell:", **style).grid(row=2, column=0, sticky="e", pady=6)
        self.cell_var = tk.StringVar(value="")
        self.cell_cb = ttk.Combobox(body, values=[], state="readonly", width=18, textvariable=self.cell_var)
        self.cell_cb.grid(row=2, column=1, sticky="w")
        self.cell_cb.bind("<<ComboboxSelected>>", self._refresh_machine_options)

        tk.Label(body, text="Machine:", **style).grid(row=2, column=2, sticky="e", pady=6)
        self.machine_var = tk.StringVar(value="")
        self.machine_cb = ttk.Combobox(body, values=[], state="readonly", width=18, textvariable=self.machine_var)
        self.machine_cb.grid(row=2, column=3, sticky="w")

        tk.Label(body, text="Part Number:", **style).grid(row=3, column=0, sticky="e", pady=6)
        self.part_var = tk.StringVar(value="")
        self.part_cb = ttk.Combobox(body, values=[], state="readonly", width=24, textvariable=self.part_var)
        self.part_cb.grid(row=3, column=1, sticky="w")

        tk.Label(body, text="Production Qty:", **style).grid(row=3, column=2, sticky="e", pady=6)
        self.shift_qty_entry = tk.Entry(body, width=18)
        self.shift_qty_entry.grid(row=3, column=3, sticky="w")

        self.has_downtime_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            body,
            text="Had Downtime",
            variable=self.has_downtime_var,
            command=self._toggle_downtime_section,
            bg=self.controller.colors["bg"],
            fg=self.controller.colors["fg"],
            activebackground=self.controller.colors["bg"],
            activeforeground=self.controller.colors["fg"],
        ).grid(row=4, column=0, sticky="w", pady=(10, 4))

        self.downtime_section = tk.Frame(body, bg=self.controller.colors["bg"])
        self.downtime_section.grid(row=5, column=0, columnspan=4, sticky="we")

        tk.Label(self.downtime_section, text="Downtime Code:", **style).grid(row=0, column=0, sticky="e", pady=6)
        self.downtime_var = tk.StringVar(value="")
        codes = list_downtime_codes_service()
        self.downtime_options = []
        self.downtime_map = {}
        for row in codes:
            code = row.get("code", "")
            desc = row.get("description", "")
            display = f"{code} - {desc}" if desc else code
            self.downtime_options.append(display)
            self.downtime_map[display] = code
        self.downtime_cb = ttk.Combobox(
            self.downtime_section,
            values=self.downtime_options,
            textvariable=self.downtime_var,
            state="readonly",
            width=32,
        )
        self.downtime_cb.grid(row=0, column=1, sticky="w")

        tk.Label(self.downtime_section, text="Total Time (min):", **style).grid(row=0, column=2, sticky="w")
        self.dt_total_entry = tk.Entry(self.downtime_section, width=10)
        self.dt_total_entry.grid(row=0, column=3, padx=(6, 12))

        tk.Label(self.downtime_section, text="# Occurrences:", **style).grid(row=0, column=4, sticky="w")
        self.dt_occ_entry = tk.Entry(self.downtime_section, width=10)
        self.dt_occ_entry.grid(row=0, column=5, padx=(6, 12))

        tk.Label(self.downtime_section, text="Comments:", **style).grid(row=0, column=6, sticky="w")
        self.dt_comment_entry = tk.Entry(self.downtime_section, width=28)
        self.dt_comment_entry.grid(row=0, column=7, padx=(6, 0))

        tk.Button(
            self.downtime_section,
            text="Add Downtime",
            command=wrap_ui_action(self.controller, "Operator", "add_downtime", self.add_downtime_entry),
            bg="#17a2b8",
            fg="white",
        ).grid(row=0, column=8, padx=(12, 0))

        tk.Button(
            self.downtime_section,
            text="Remove Selected",
            command=wrap_ui_action(self.controller, "Operator", "remove_downtime", self.remove_downtime_entry),
            bg="#dc3545",
            fg="white",
        ).grid(row=0, column=9, padx=(8, 0))

        self.downtime_tree = ttk.Treeview(
            body,
            columns=("code", "minutes", "occurrences", "comments"),
            show="headings",
            height=6,
        )
        for col, width in (
            ("code", 180),
            ("minutes", 100),
            ("occurrences", 120),
            ("comments", 260),
        ):
            self.downtime_tree.heading(col, text=col.upper())
            self.downtime_tree.column(col, width=width)
        self.downtime_tree.grid(row=6, column=0, columnspan=4, sticky="we", pady=(6, 10))

        self._toggle_downtime_section()
        self._refresh_line_dependent_fields()

        tk.Button(
            body,
            text="Submit Shift Report",
            command=wrap_ui_action(self.controller, "Operator", "submit_shift_report", self.submit_shift_report),
            bg="#28a745",
            fg="white",
            font=("Arial", 12, "bold"),
            width=20,
        ).grid(row=7, column=0, columnspan=4, pady=20, sticky="w")

    def _toggle_downtime_section(self):
        if self.has_downtime_var.get():
            self.downtime_section.grid()
            self.downtime_tree.grid()
        else:
            self.downtime_var.set("")
            for entry in (self.dt_total_entry, self.dt_occ_entry, self.dt_comment_entry):
                entry.delete(0, "end")
            for row in self.downtime_tree.get_children():
                self.downtime_tree.delete(row)
            self.downtime_section.grid_remove()
            self.downtime_tree.grid_remove()

    def _refresh_line_dependent_fields(self, event=None):
        line = self.shift_line_cb.get().strip()
        cells = list_cells(line)
        self.cell_cb.configure(values=cells)
        if cells:
            self.cell_cb.set(cells[0])
        else:
            self.cell_cb.set("")
        parts = list_parts(line)
        self.part_cb.configure(values=parts)
        if parts:
            self.part_cb.set(parts[0])
        else:
            self.part_cb.set("")
        self._refresh_machine_options()

    def _refresh_machine_options(self, event=None):
        line = self.shift_line_cb.get().strip()
        machines = list_machines(line)
        self.machine_cb.configure(values=machines)
        if machines:
            self.machine_cb.set(machines[0])
        else:
            self.machine_cb.set("")

    def add_downtime_entry(self):
        if not self.has_downtime_var.get():
            messagebox.showerror("No Downtime", "Check 'Had Downtime' to add entries.")
            return
        display = self.downtime_var.get().strip()
        if not display:
            messagebox.showerror("Missing Info", "Select a downtime code.")
            return
        minutes = safe_float(self.dt_total_entry.get(), 0.0)
        if minutes <= 0:
            messagebox.showerror("Missing Info", "Enter downtime minutes.")
            return
        occurrences = safe_int(self.dt_occ_entry.get(), 0)
        comments = self.dt_comment_entry.get().strip()
        self.downtime_tree.insert(
            "",
            "end",
            values=(display, f"{minutes:.1f}", occurrences, comments),
        )
        self.downtime_var.set("")
        self.dt_total_entry.delete(0, "end")
        self.dt_occ_entry.delete(0, "end")
        self.dt_comment_entry.delete(0, "end")

    def remove_downtime_entry(self):
        sel = self.downtime_tree.selection()
        if not sel:
            return
        for item in sel:
            self.downtime_tree.delete(item)

    def submit_shift_report(self):
        line = self.shift_line_cb.get().strip()
        cell = self.cell_cb.get().strip()
        part_number = self.part_cb.get().strip()
        machine = self.machine_cb.get().strip()
        qty = safe_int(self.shift_qty_entry.get(), 0)
        if not line:
            messagebox.showerror("Missing Info", "Select a line.")
            return
        if not cell:
            messagebox.showerror("Missing Info", "Select a cell.")
            return
        if not part_number:
            messagebox.showerror("Missing Info", "Select a part number.")
            return
        if qty <= 0:
            messagebox.showerror("Missing Info", "Enter the production quantity.")
            return

        downtime_entries = []
        downtime_total = 0.0
        if self.has_downtime_var.get():
            for row in self.downtime_tree.get_children():
                display, minutes, occurrences, comments = self.downtime_tree.item(row, "values")
                code = self.downtime_map.get(display, display.split(" - ")[0])
                entry_minutes = safe_float(minutes, 0.0)
                downtime_total += entry_minutes
                downtime_entries.append(
                    {
                        "code": code,
                        "minutes": entry_minutes,
                        "occurrences": safe_int(occurrences, 0),
                        "comments": comments or "",
                    }
                )
            if not downtime_entries:
                messagebox.showerror("Missing Info", "Add at least one downtime entry.")
                return

        now = datetime.now()
        entry_id = f"SP-{now.strftime('%Y%m%d-%H%M%S')}"
        new_row = {
            "ID": entry_id,
            "Date": now.strftime("%Y-%m-%d"),
            "Time": now.strftime("%H:%M:%S"),
            "Shift": self.shift_cb.get(),
            "Line": line,
            "Cell": cell,
            "Machine": machine,
            "Part_Number": part_number,
            "Tool_Num": "",
            "Reason": "Shift Production",
            "Downtime_Mins": downtime_total,
            "Production_Qty": float(qty),
            "Cost": 0.0,
            "Tool_Life": 0.0,
            "Tool_Changer": self.controller.user or "",
            "Defects_Present": "No",
            "Defect_Qty": 0,
            "Sort_Done": "No",
            "Defect_Reason": "",
            "Quality_Verified": "N/A",
            "Quality_User": "",
            "Quality_Time": "",
            "Leader_Sign": "Pending",
            "Leader_User": "",
            "Leader_Time": "",
            "Serial_Numbers": "",
        }
        create_shift_report(
            new_row,
            downtime_entries,
            actor_user={"username": self.controller.user, "role": self.controller.role},
        )

        messagebox.showinfo("Saved", "Shift production report submitted for leader signoff.")
        self.shift_qty_entry.delete(0, "end")
        self.has_downtime_var.set(False)
        self._toggle_downtime_section()
