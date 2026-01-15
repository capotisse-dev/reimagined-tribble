# app/ui_machine_history.py
from __future__ import annotations

import os
import shutil
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import DATA_DIR
from .db import get_machine_id_for_line, list_print_files, list_program_files
from .services.program_revision_service import (
    create_program_file,
    list_program_revisions_service,
    rollback_program_revision,
)
from .services.print_revision_service import (
    create_print_file,
    list_print_revisions_service,
    rollback_print_revision,
)
from .services.tool_life_service import list_lines_service, list_machines


PROGRAM_EXTENSIONS = (".txt", ".nc", ".tap", ".cnc")
PRINT_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")


def _normalize_doc_name(filename: str) -> str:
    base = Path(filename).stem
    base = base.replace("_", " ").strip()
    return " ".join(base.split())


def _get_username(controller) -> str:
    username = getattr(controller, "user", "") or ""
    if username:
        return username
    try:
        return os.getlogin()
    except OSError:
        return "Unknown"


class MachineHistoryUI(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=controller.colors["bg"])
        self.controller = controller
        self.readonly = not controller.can_edit_screen("Master Data")
        self._selected_doc_name: str | None = None
        self._selected_doc_type: str | None = None

        self._build_filters()
        self._build_layout()
        self._apply_readonly()
        self.refresh_documents()

    def _build_filters(self) -> None:
        filters = tk.Frame(self, bg=self.controller.colors["bg"], padx=10, pady=8)
        filters.pack(fill="x")

        tk.Label(filters, text="Line", bg=self.controller.colors["bg"], fg=self.controller.colors["fg"]).pack(side="left")
        self.line_var = tk.StringVar()
        self.line_combo = ttk.Combobox(
            filters,
            textvariable=self.line_var,
            values=list_lines_service(),
            state="readonly",
            width=14,
        )
        self.line_combo.pack(side="left", padx=6)
        self.line_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_machine_options())

        tk.Label(filters, text="Machine", bg=self.controller.colors["bg"], fg=self.controller.colors["fg"]).pack(side="left")
        self.machine_var = tk.StringVar()
        self.machine_combo = ttk.Combobox(filters, textvariable=self.machine_var, values=[], state="readonly", width=16)
        self.machine_combo.pack(side="left", padx=6)
        self.machine_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_documents())

        tk.Label(filters, text="Type", bg=self.controller.colors["bg"], fg=self.controller.colors["fg"]).pack(side="left")
        self.type_var = tk.StringVar(value="All")
        self.type_combo = ttk.Combobox(
            filters,
            textvariable=self.type_var,
            values=["All", "Programs", "Prints"],
            state="readonly",
            width=10,
        )
        self.type_combo.pack(side="left", padx=6)
        self.type_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_documents())

        tk.Label(filters, text="Search", bg=self.controller.colors["bg"], fg=self.controller.colors["fg"]).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(filters, textvariable=self.search_var, width=24)
        self.search_entry.pack(side="left", padx=6)
        self.search_var.trace_add("write", lambda *_: self.refresh_documents())

        actions = tk.Frame(self, bg=self.controller.colors["bg"], padx=10, pady=6)
        actions.pack(fill="x")
        self.import_program_btn = tk.Button(actions, text="Import Program(s)", command=self._import_programs)
        self.import_program_btn.pack(side="left")
        self.import_print_btn = tk.Button(actions, text="Import Print(s)", command=self._import_prints)
        self.import_print_btn.pack(side="left", padx=6)
        self.delete_btn = tk.Button(actions, text="Delete Document", command=self._delete_document)
        self.delete_btn.pack(side="right")

    def _build_layout(self) -> None:
        container = tk.Frame(self, bg=self.controller.colors["bg"], padx=10, pady=6)
        container.pack(fill="both", expand=True)

        self.paned = ttk.Panedwindow(container, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        left = tk.Frame(self.paned, bg=self.controller.colors["bg"])
        right = tk.Frame(self.paned, bg=self.controller.colors["bg"])
        self.paned.add(left, weight=3)
        self.paned.add(right, weight=2)

        cols = ("name", "type", "rev", "updated", "updated_by")
        self.doc_tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        for col, heading, width in [
            ("name", "Document Name", 220),
            ("type", "Type", 90),
            ("rev", "Current Rev", 90),
            ("updated", "Last Updated", 140),
            ("updated_by", "Last Updated By", 140),
        ]:
            self.doc_tree.heading(col, text=heading)
            self.doc_tree.column(col, width=width, anchor="w")
        self.doc_tree.pack(fill="both", expand=True)
        self.doc_tree.bind("<<TreeviewSelect>>", lambda _e: self._load_document_details())

        detail_header = tk.Label(
            right,
            text="Revision History",
            bg=self.controller.colors["bg"],
            fg=self.controller.colors["fg"],
            font=("Arial", 12, "bold"),
        )
        detail_header.pack(anchor="w", pady=(0, 6))

        rev_cols = ("rev", "date", "user", "filename")
        self.rev_tree = ttk.Treeview(right, columns=rev_cols, show="headings", height=14)
        for col, heading, width in [
            ("rev", "Rev", 60),
            ("date", "Date", 130),
            ("user", "User", 120),
            ("filename", "Original Filename", 220),
        ]:
            self.rev_tree.heading(col, text=heading)
            self.rev_tree.column(col, width=width, anchor="w")
        self.rev_tree.pack(fill="both", expand=True, pady=(0, 6))

        detail_actions = tk.Frame(right, bg=self.controller.colors["bg"])
        detail_actions.pack(fill="x")
        self.export_current_btn = tk.Button(detail_actions, text="Export Current", command=self._export_current)
        self.export_current_btn.pack(side="left")
        self.export_selected_btn = tk.Button(detail_actions, text="Export Selected Revision", command=self._export_selected_revision)
        self.export_selected_btn.pack(side="left", padx=6)
        self.open_btn = tk.Button(detail_actions, text="Open/Preview", command=self._open_selected)
        self.open_btn.pack(side="left", padx=6)
        self.recall_btn = tk.Button(detail_actions, text="Recall Selected Revision", command=self._recall_selected)
        self.recall_btn.pack(side="right")

    def _apply_readonly(self) -> None:
        if not self.readonly:
            return
        self.import_program_btn.configure(state="disabled")
        self.import_print_btn.configure(state="disabled")
        self.delete_btn.configure(state="disabled")

    def _refresh_machine_options(self) -> None:
        line = self.line_var.get()
        machines = list_machines(line)
        self.machine_combo.configure(values=machines)
        if machines:
            self.machine_var.set(machines[0])
        else:
            self.machine_var.set("")
        self.refresh_documents()

    def _doc_type_filter(self) -> str | None:
        choice = self.type_var.get()
        if choice == "Programs":
            return "program"
        if choice == "Prints":
            return "print"
        return None

    def refresh_documents(self) -> None:
        for item in self.doc_tree.get_children():
            self.doc_tree.delete(item)
        self._selected_doc_name = None
        self._selected_doc_type = None
        for item in self.rev_tree.get_children():
            self.rev_tree.delete(item)

        line = self.line_var.get().strip()
        machine = self.machine_var.get().strip()
        if not line or not machine:
            return

        machine_id = get_machine_id_for_line(line, machine)
        if machine_id is None:
            return

        doc_type = self._doc_type_filter()
        search = self.search_var.get().strip()
        rows: list[dict] = []
        if doc_type in (None, "program"):
            for row in list_program_files("MACHINE", machine_id, search=search):
                row["_doc_type"] = "program"
                rows.append(row)
        if doc_type in (None, "print"):
            for row in list_print_files("MACHINE", machine_id, search=search):
                row["_doc_type"] = "print"
                rows.append(row)

        for row in rows:
            doc_type_key = row.get("_doc_type", "program")
            doc_type_label = "Program" if doc_type_key == "program" else "Print"
            doc_name = row.get("filename", "")
            rev = row.get("revision") or ""
            updated = row.get("created_at") or ""
            updated_by = row.get("created_by") or ""
            iid = f"{doc_type_key}:{doc_name}"
            self.doc_tree.insert(
                "",
                "end",
                iid=iid,
                values=(doc_name, doc_type_label, rev, updated, updated_by),
            )

    def _load_document_details(self) -> None:
        selection = self.doc_tree.selection()
        if not selection:
            return
        iid = selection[0]
        if ":" in iid:
            doc_type_key, doc_name = iid.split(":", 1)
        else:
            doc_type_key, doc_name = "program", iid
        self._selected_doc_name = doc_name
        self._selected_doc_type = doc_type_key

        for item in self.rev_tree.get_children():
            self.rev_tree.delete(item)
        line = self.line_var.get().strip()
        machine = self.machine_var.get().strip()
        machine_id = get_machine_id_for_line(line, machine)
        if machine_id is None:
            return
        if self._selected_doc_type == "program":
            revisions = list_program_revisions_service("MACHINE", doc_name, machine_id)
        else:
            revisions = list_print_revisions_service("MACHINE", doc_name, machine_id)
        for rev in revisions:
            self.rev_tree.insert(
                "",
                "end",
                iid=str(rev["id"]),
                values=(
                    rev.get("revision", ""),
                    rev.get("created_at", ""),
                    rev.get("created_by", ""),
                    Path(rev.get("file_path", "")).name,
                ),
            )

    def _require_line_machine(self) -> tuple[str, str] | None:
        line = self.line_var.get().strip()
        machine = self.machine_var.get().strip()
        if not line or not machine:
            messagebox.showwarning("Selection required", "Select both a line and machine first.")
            return None
        return line, machine

    def _import_programs(self) -> None:
        self._import_documents("program")

    def _import_prints(self) -> None:
        self._import_documents("print")

    def _import_documents(self, doc_type: str) -> None:
        if self.readonly:
            return
        selection = self._require_line_machine()
        if not selection:
            return
        line, machine = selection
        machine_id = get_machine_id_for_line(line, machine)
        if machine_id is None:
            messagebox.showerror("Missing Machine", "Unable to resolve machine ID.")
            return

        if doc_type == "program":
            filetypes = [("Programs", "*.txt *.nc *.tap *.cnc"), ("All files", "*.*")]
        else:
            filetypes = [("Prints", "*.pdf *.png *.jpg *.jpeg"), ("All files", "*.*")]

        paths = filedialog.askopenfilenames(title="Import Documents", filetypes=filetypes)
        if not paths:
            return
        user = _get_username(self.controller)
        for path in paths:
            try:
                self._save_document(path, machine_id, doc_type, user)
            except Exception as exc:
                messagebox.showerror("Import Failed", f"Failed to import {path}\n{exc}")
        self.refresh_documents()

    def _save_document(self, source_path: str, machine_id: int, doc_type: str, user: str) -> None:
        doc_name = _normalize_doc_name(os.path.basename(source_path))
        actor = {"username": user, "role": getattr(self.controller, "role", "") or ""}
        if doc_type == "program":
            status, _ = create_program_file(
                source_path=source_path,
                filename=doc_name,
                scope_type="MACHINE",
                machine_id=machine_id,
                actor_user=actor,
            )
        else:
            status, _ = create_print_file(
                source_path=source_path,
                filename=doc_name,
                scope_type="MACHINE",
                machine_id=machine_id,
                actor_user=actor,
            )
        if status == "DUPLICATE":
            raise ValueError(f"{doc_name} is already stored with identical content.")

    def _selected_revision(self) -> dict | None:
        if not self._selected_doc_name or not self._selected_doc_type:
            return None
        selection = self.rev_tree.selection()
        if not selection:
            return None
        revision_id = int(selection[0])
        line = self.line_var.get().strip()
        machine = self.machine_var.get().strip()
        machine_id = get_machine_id_for_line(line, machine)
        if machine_id is None:
            return None
        if self._selected_doc_type == "program":
            revisions = list_program_revisions_service("MACHINE", self._selected_doc_name, machine_id)
        else:
            revisions = list_print_revisions_service("MACHINE", self._selected_doc_name, machine_id)
        return next((rev for rev in revisions if rev["id"] == revision_id), None)

    def _get_current_revision(self) -> dict | None:
        if not self._selected_doc_name or not self._selected_doc_type:
            return None
        line = self.line_var.get().strip()
        machine = self.machine_var.get().strip()
        machine_id = get_machine_id_for_line(line, machine)
        if machine_id is None:
            return None
        if self._selected_doc_type == "program":
            revisions = list_program_revisions_service("MACHINE", self._selected_doc_name, machine_id)
        else:
            revisions = list_print_revisions_service("MACHINE", self._selected_doc_name, machine_id)
        return revisions[0] if revisions else None

    def _resolve_path(self, stored_path: str) -> Path:
        return Path(DATA_DIR) / stored_path

    def _export_current(self) -> None:
        revision = self._get_current_revision()
        if not revision:
            messagebox.showinfo("Export", "Select a document first.")
            return
        self._export_revision(revision)

    def _export_selected_revision(self) -> None:
        revision = self._selected_revision()
        if not revision:
            messagebox.showinfo("Export", "Select a revision first.")
            return
        self._export_revision(revision)

    def _export_revision(self, revision: dict) -> None:
        target_dir = filedialog.askdirectory(title="Select export folder")
        if not target_dir:
            return
        stored_path = self._resolve_path(revision["file_path"])
        if not stored_path.exists():
            messagebox.showerror("Export Failed", "Stored file not found.")
            return
        ext = stored_path.suffix
        doc_name = self._selected_doc_name or "document"
        filename = f"{doc_name}_rev{revision['revision']}{ext}"
        target_path = Path(target_dir) / filename
        shutil.copy2(stored_path, target_path)
        messagebox.showinfo("Exported", f"Exported to {target_path}")

    def _open_selected(self) -> None:
        revision = self._selected_revision() or self._get_current_revision()
        if not revision:
            messagebox.showinfo("Open", "Select a document or revision first.")
            return
        stored_path = self._resolve_path(revision["file_path"])
        if not stored_path.exists():
            messagebox.showerror("Open Failed", "Stored file not found.")
            return
        if self._selected_doc_type == "program":
            self._open_text_viewer(stored_path)
        else:
            webbrowser.open(stored_path.as_uri())

    def _open_text_viewer(self, path: Path) -> None:
        top = tk.Toplevel(self)
        top.title(f"Program Viewer - {path.name}")
        top.geometry("700x500")
        text = tk.Text(top, wrap="none")
        text.pack(fill="both", expand=True)
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text.insert("1.0", handle.read())
        text.configure(state="disabled")

    def _recall_selected(self) -> None:
        if self.readonly:
            return
        revision = self._selected_revision()
        if not revision:
            messagebox.showinfo("Recall", "Select a revision to recall.")
            return
        if not self._selected_doc_name or not self._selected_doc_type:
            return
        line_machine = self._require_line_machine()
        if not line_machine:
            return
        line, machine = line_machine
        machine_id = get_machine_id_for_line(line, machine)
        if machine_id is None:
            return
        actor = {"username": _get_username(self.controller), "role": getattr(self.controller, "role", "") or ""}
        if self._selected_doc_type == "program":
            rollback_program_revision(
                scope_type="MACHINE",
                filename=self._selected_doc_name,
                machine_id=machine_id,
                target_revision_id=revision["id"],
                actor_user=actor,
            )
        else:
            rollback_print_revision(
                scope_type="MACHINE",
                filename=self._selected_doc_name,
                machine_id=machine_id,
                target_revision_id=revision["id"],
                actor_user=actor,
            )
        self._load_document_details()
        self.refresh_documents()

    def _delete_document(self) -> None:
        if self.readonly:
            return
        selection = self.doc_tree.selection()
        if not selection:
            messagebox.showinfo("Delete", "Select a document first.")
            return
        iid = selection[0]
        if ":" in iid:
            doc_type, doc_name = iid.split(":", 1)
        else:
            doc_type, doc_name = "program", iid
        if not messagebox.askyesno("Deactivate Document", "Mark this document as inactive?"):
            return
        line = self.line_var.get().strip()
        machine = self.machine_var.get().strip()
        machine_id = get_machine_id_for_line(line, machine)
        if machine_id is None:
            return
        if doc_type == "program":
            from ..db import deactivate_program_revisions

            deactivate_program_revisions("MACHINE", doc_name, machine_id)
        else:
            from ..db import deactivate_print_revisions

            deactivate_print_revisions("MACHINE", doc_name, machine_id)
        self.refresh_documents()
