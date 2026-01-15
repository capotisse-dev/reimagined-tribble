import tkinter as tk
from tkinter import ttk
from .storage import list_month_files

LIGHT = {"bg": "#f0f0f0", "fg": "black", "header_bg": "#cccccc"}
DARK = {"bg": "#2e2e2e", "fg": "white", "header_bg": "#1a1a1a"}


class HeaderFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, height=70)
        self.pack_propagate(False)

        info = f"User: {controller.user} ({controller.role})"
        ttk.Label(self, text=info, style="Header.TLabel").pack(side="left", padx=20)

        right = ttk.Frame(self)
        right.pack(side="right", padx=10)

        mode_text = "Light Mode" if controller.is_dark else "Dark Mode"
        ttk.Button(right, text=mode_text, command=controller.toggle_theme, width=12).pack(side="left", padx=6)
        if getattr(controller, "can_edit_layout", lambda: False)():
            ttk.Button(right, text="Style", command=controller.open_style_editor, width=10).pack(
                side="left", padx=6
            )
        ttk.Button(right, text="Logout", command=controller.logout, style="Danger.TButton").pack(
            side="left", padx=6
        )

class FilePicker(tk.Frame):
    def __init__(self, parent, on_change):
        super().__init__(parent)
        tk.Label(self, text="Month/File:").pack(side="left", padx=6)
        self.cb = ttk.Combobox(self, values=list_month_files(), state="readonly", width=28)
        self.cb.pack(side="left", padx=6)
        self.cb.current(0)
        self.cb.bind("<<ComboboxSelected>>", lambda e: on_change(self.cb.get()))
        ttk.Button(self, text="Reload", command=lambda: on_change(self.cb.get())).pack(side="left", padx=6)

    def get(self):
        return self.cb.get()

class DataTable(tk.Frame):
    def __init__(self, parent, columns):
        super().__init__(parent)
        self.columns = columns
        self.tree = ttk.Treeview(self, columns=columns, show="headings")

        for c in columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110)

        sy = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=sy.set, xscroll=sx.set)

        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

    def load(self, df):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=[row.get(c, "") for c in self.columns])

    def selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return vals[0] if vals else None
