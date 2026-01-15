from __future__ import annotations

import tkinter as tk

from .ui_super import _SideNavUI


class UIDEUI(_SideNavUI):
    """UIDE role: super access with layout styling controls."""
    def __init__(self, parent, controller, show_header=True):
        super().__init__(parent, controller, show_header=show_header)
        if not isinstance(self, tk.Frame):
            return
