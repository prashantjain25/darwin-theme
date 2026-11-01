#!/usr/bin/env python3
"""Build the LXQt panel layout (menu bar on top, dock at the bottom).

usage: panel.py PANEL_CONF [--menubar] [--dock] --bar-h N --dock-h N --dock-icon N
                [--dock-w N] [--start-icon PATH] [--app DESKTOP_FILE ...]

Run it while lxqt-panel is NOT running (the panel rewrites its config on exit).
Existing plugin sections (tray, volume, ...) are kept; only the keys we manage
are replaced.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ini import set_keys  # noqa: E402


def read(path):
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def drop_section(text, name):
    return re.sub(r"^\[%s\]\n.*?(?=^\[|\Z)" % re.escape(name), "", text, flags=re.S | re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("conf")
    ap.add_argument("--menubar", action="store_true")
    ap.add_argument("--dock", action="store_true")
    ap.add_argument("--bar-h", type=int, default=34)
    ap.add_argument("--dock-h", type=int, default=62)
    ap.add_argument("--dock-icon", type=int, default=36)
    ap.add_argument("--dock-w", type=int, default=290)
    ap.add_argument("--start-icon", default="")
    ap.add_argument("--clock-format", default="ddd MMM d  h:mm AP")
    ap.add_argument("--app", action="append", default=[])
    ap.add_argument("--mode", default="dark", choices=["dark", "light"])
    ap.add_argument("--sep-after", type=int, default=0, help="draw a separator after this many apps")
    a = ap.parse_args()

    conf = a.conf
    panels = []
    if a.menubar:
        panels.append("panel1")
    if a.dock:
        panels.append("panel2")

    # [General] panels list. If only one element is requested keep the other panel if it exists.
    text = read(conf)
    m = re.search(r"^panels=(.*)$", text, re.M)
    existing = [p.strip() for p in m.group(1).split(",")] if m else []
    for p in existing:
        if p and p not in panels:
            panels.append(p)
    panels = sorted(set(panels), key=lambda p: int(re.sub(r"\D", "", p) or 0))
    set_keys(conf, "General", [("__userfile__", "true"), ("panels", ", ".join(panels))])

    if a.menubar:
        set_keys(conf, "panel1", [
            ("alignment", "-1"), ("animation-duration", "0"), ("hidable", "false"),
            ("iconSize", "16"), ("lineCount", "1"), ("lockPanel", "true"), ("opacity", "100"),
            ("panelSize", str(a.bar_h)),
            ("plugins", "fancymenu, spacer, statusnotifier, tray, volume, mount, worldclock"),
            ("position", "Top"), ("reserve-space", "true"), ("visible-margin", "true"),
            ("width", "100"), ("width-percent", "true"),
        ])
        fm = [("alignment", "Left"), ("showText", "false")]
        if a.start_icon:
            fm += [("ownIcon", "true"), ("icon", a.start_icon)]
        set_keys(conf, "fancymenu", fm)
        set_keys(conf, "spacer", [("alignment", "Left"), ("expandable", "true"), ("spaceType", "invisible")])
        # one-line clock: "Sun Nov 1  11:16 PM"
        set_keys(conf, "worldclock", [
            ("alignment", "Right"), ("autoRotate", "false"), ("formatType", "custom"),
            ("customFormat", '"%s"' % a.clock_format),
        ])

    if a.dock:
        set_keys(conf, "panel2", [
            ("background-color", "#f6f6f6" if a.mode == "light" else "#4a4a4a"),   # Figma dock fill
            ("opacity", "36" if a.mode == "light" else "39"),
            ("alignment", "0"), ("animation-duration", "0"), ("hidable", "false"),
            ("iconSize", str(a.dock_icon)), ("lineCount", "1"), ("lockPanel", "true"),
            ("panelSize", str(a.dock_h)), ("plugins", "quicklaunch"),
            ("position", "Bottom"), ("reserve-space", "true"), ("visible-margin", "true"),
            ("width", str(a.dock_w)), ("width-percent", "false"),
        ])
        text = read(conf)
        for name in ("quicklaunch", "quicklaunch2", "spacer2"):
            text = drop_section(text, name)

        def group(name, apps, typ):
            block = "[%s]\ntype=%s\nalignment=Left\n" % (name, typ)
            for i, desk in enumerate(apps, 1):
                block += "apps\\%d\\desktop=%s\n" % (i, desk)
            return block + "apps\\size=%d\n" % len(apps)

        if 0 < a.sep_after < len(a.app):
            # LXQt plugin instances with a numeric suffix need an explicit type=
            plugins = "quicklaunch, spacer2, quicklaunch2"
            blocks = [group("quicklaunch", a.app[:a.sep_after], "quicklaunch"),
                      "[spacer2]\ntype=spacer\nalignment=Left\nexpandable=false\nspaceType=lined\n",
                      group("quicklaunch2", a.app[a.sep_after:], "quicklaunch")]
        else:
            plugins = "quicklaunch"
            blocks = [group("quicklaunch", a.app, "quicklaunch")]
        text = text.rstrip("\n") + "\n\n" + "\n".join(blocks)
        open(conf, "w", encoding="utf-8").write(text)
        set_keys(conf, "panel2", [("plugins", plugins)])

    print("panel config written:", conf, "| panels =", ", ".join(panels))


if __name__ == "__main__":
    main()
