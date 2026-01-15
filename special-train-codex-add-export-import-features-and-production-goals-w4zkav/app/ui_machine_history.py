# app/ui_machine_history.py
from __future__ import annotations

import hashlib
import os
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import DATA_DIR
from .db import (
    add_machine_document_revision,
    create_machine_document,
    find_machine_document_by_name_or_hash,
    get_next_machine_document_revision_number,
    list_lines,
    list_machine_document_revisions,
    list_machine_documents,
    list_machines_for_line,
    set_machine_document_active,
)


PROGRAM_EXTENSIONS = (".txt", ".nc", ".tap", ".cnc")
PRINT_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")


def _normalize_doc_name(filename: str) -> str:
    base = Path(filename).stem
    base = base.replace("_", " ").strip()
    return " ".join(base.split())


def _safe_folder_name(value: str) -> str:
    safe = value.replace(os.sep, "_")
    if os.altsep:
        safe = safe.replace(os.altsep, "_")
    return safe.replace(" ", "_") or "document"


def _hash_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        self._selected_document_id: int | None = None
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
        self.line_combo = ttk.Combobox(filters, textvariable=self.line_var, values=list_lines(), state="readonly", width=14)
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
        machines = list_machines_for_line(line)
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
        self._selected_document_id = None
        self._selected_doc_type = None
        for item in self.rev_tree.get_children():
            self.rev_tree.delete(item)

        line = self.line_var.get().strip()
        machine = self.machine_var.get().strip()
        if not line or not machine:
            return

        doc_type = self._doc_type_filter()
        search = self.search_var.get().strip()
        rows = list_machine_documents(line, machine, doc_type=doc_type, search=search)
        for row in rows:
            doc_id = row["id"]
            doc_type_label = "Program" if row["doc_type"] == "program" else "Print"
            rev = row.get("current_revision") or ""
            updated = row.get("revision_created_at") or row.get("created_at") or ""
            updated_by = row.get("revision_created_by") or row.get("created_by") or ""
            self.doc_tree.insert(
                "",
                "end",
                iid=str(doc_id),
                values=(row["doc_name"], doc_type_label, rev, updated, updated_by),
            )

    def _load_document_details(self) -> None:
        selection = self.doc_tree.selection()
        if not selection:
            return
        doc_id = int(selection[0])
        self._selected_document_id = doc_id
        doc_type_label = self.doc_tree.item(selection[0], "values")[1]
        self._selected_doc_type = "program" if doc_type_label == "Program" else "print"

        for item in self.rev_tree.get_children():
            self.rev_tree.delete(item)
        for rev in list_machine_document_revisions(doc_id):
            self.rev_tree.insert(
                "",
                "end",
                iid=str(rev["id"]),
                values=(
                    rev["revision_number"],
                    rev["created_at"],
                    rev["created_by"],
                    rev["original_filename"],
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
                self._save_document(path, line, machine, doc_type, user)
            except Exception as exc:
                messagebox.showerror("Import Failed", f"Failed to import {path}\n{exc}")
        self.refresh_documents()

    def _save_document(self, source_path: str, line: str, machine: str, doc_type: str, user: str) -> None:
        doc_name = _normalize_doc_name(os.path.basename(source_path))
        file_hash = _hash_file(source_path)
        existing = find_machine_document_by_name_or_hash(line, machine, doc_type, doc_name, file_hash)

        if existing:
            document_id = existing["id"]
        else:
            document_id = create_machine_document(line, machine, doc_type, doc_name, user)

        revision_number = get_next_machine_document_revision_number(document_id)
        stored_path = self._store_file(source_path, line, machine, doc_type, doc_name, revision_number)
        add_machine_document_revision(
            document_id=document_id,
            revision_number=revision_number,
            stored_path=stored_path,
            original_filename=os.path.basename(source_path),
            file_hash=file_hash,
            created_by=user,
            notes=None,
        )

    def _store_file(
        self,
        source_path: str,
        line: str,
        machine: str,
        doc_type: str,
        doc_name: str,
        revision_number: int,
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        ext = Path(source_path).suffix
        target_dir = Path(DATA_DIR) / "storage" / _safe_folder_name(line) / _safe_folder_name(machine) / doc_type / _safe_folder_name(doc_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"rev_{revision_number}_{timestamp}{ext}"
        shutil.copy2(source_path, target_path)
        return str(target_path.relative_to(DATA_DIR))

    def _selected_revision(self) -> dict | None:
        if self._selected_document_id is None:
            return None
        selection = self.rev_tree.selection()
        if not selection:
            return None
        revision_id = int(selection[0])
        revisions = list_machine_document_revisions(self._selected_document_id)
        return next((rev for rev in revisions if rev["id"] == revision_id), None)

    def _get_current_revision(self) -> dict | None:
        if self._selected_document_id is None:
            return None
        revisions = list_machine_document_revisions(self._selected_document_id)
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
        stored_path = self._resolve_path(revision["stored_path"])
        if not stored_path.exists():
            messagebox.showerror("Export Failed", "Stored file not found.")
            return
        ext = stored_path.suffix
        doc_name = self.doc_tree.item(str(self._selected_document_id), "values")[0]
        filename = f"{doc_name}_rev{revision['revision_number']}{ext}"
        target_path = Path(target_dir) / filename
        shutil.copy2(stored_path, target_path)
        messagebox.showinfo("Exported", f"Exported to {target_path}")

    def _open_selected(self) -> None:
        revision = self._selected_revision() or self._get_current_revision()
        if not revision:
            messagebox.showinfo("Open", "Select a document or revision first.")
            return
        stored_path = self._resolve_path(revision["stored_path"])
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
        if self._selected_document_id is None:
            return
        stored_path = self._resolve_path(revision["stored_path"])
        if not stored_path.exists():
            messagebox.showerror("Recall Failed", "Stored file not found.")
            return
        line_machine = self._require_line_machine()
        if not line_machine:
            return
        line, machine = line_machine
        doc_name = self.doc_tree.item(str(self._selected_document_id), "values")[0]
        user = _get_username(self.controller)
        revision_number = get_next_machine_document_revision_number(self._selected_document_id)
        new_path = self._store_file(str(stored_path), line, machine, self._selected_doc_type or "program", doc_name, revision_number)
        file_hash = _hash_file(str(stored_path))
        add_machine_document_revision(
            document_id=self._selected_document_id,
            revision_number=revision_number,
            stored_path=new_path,
            original_filename=revision.get("original_filename", ""),
            file_hash=file_hash,
            created_by=user,
            notes="Recalled previous revision",
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
        doc_id = int(selection[0])
        if not messagebox.askyesno("Deactivate Document", "Mark this document as inactive?"):
            return
        set_machine_document_active(doc_id, False)
        self.refresh_documents()
