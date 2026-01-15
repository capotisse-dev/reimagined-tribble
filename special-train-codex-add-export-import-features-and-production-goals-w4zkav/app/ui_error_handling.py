from __future__ import annotations

import logging
import traceback
from typing import Callable, Any
from tkinter import messagebox

from .audit import log_audit
from .exceptions import PermissionDenied, ValidationError, NotFoundError
from .logging_config import configure_logging, log_with_user


logger = configure_logging()


def wrap_ui_action(controller, screen: str, action: str, func: Callable[..., Any]):
    """Wrap UI callbacks to log exceptions, show dialogs, and audit failures."""

    def _wrapped(*args, **kwargs):
        user = getattr(controller, "user", "") or ""
        try:
            return func(*args, **kwargs)
        except (PermissionDenied, ValidationError, NotFoundError) as exc:
            messagebox.showerror("Action Denied", str(exc))
            log_audit(user, f"Denied {screen}::{action} - {exc}")
            return None
        except Exception as exc:
            messagebox.showerror("Unexpected Error", "An unexpected error occurred. Please try again.")
            stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            log_with_user(logger, logging.ERROR, f"{screen}:{action} failed\n{stack}", user=user)
            log_audit(user, f"Error in {screen}::{action} - {exc}")
            return None

    return _wrapped
