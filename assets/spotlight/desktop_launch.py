"""Gio executes desktop files; Spotlight never interprets Exec as shell text.
SPDX-License-Identifier: MIT
"""
from pathlib import Path


def launch_application(desktop_file: str, activation_token: str = "") -> None:
    import gi
    import warnings
    # Older PyGObject with newer GLib emits this while importing its own overrides.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"GLib\.unix_signal_add_full is deprecated.*",
                                category=gi.PyGIDeprecationWarning)
        from gi.repository import Gio
    try:
        gi.require_version("GioUnix", "2.0")
        from gi.repository import GioUnix
        desktop_info = GioUnix.DesktopAppInfo
    except (ImportError, ValueError):  # GLib before the GioUnix namespace split.
        desktop_info = Gio.DesktopAppInfo
    path = Path(desktop_file)
    if not path.is_file() or path.suffix != ".desktop":
        raise ValueError("Desktop entry is unavailable")
    info = desktop_info.new_from_filename(str(path.absolute()))
    if info is None:
        raise ValueError("Invalid desktop entry")
    context = Gio.AppLaunchContext()
    if activation_token:
        context.setenv("XDG_ACTIVATION_TOKEN", activation_token)
    try:
        if not info.launch([], context):
            raise RuntimeError("Application could not be started")
    except Exception as exc:
        raise RuntimeError("Application could not be started") from exc
