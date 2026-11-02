#!/usr/bin/env python3
"""Patch an Openbox rc.xml: theme name, title-bar button layout, window title font size.

usage: openbox_rc.py RC_XML THEME_NAME [FONT_SIZE] [FONT_FAMILY]
"""
import re
import sys


def patch(path, theme, size, font="Inter", switcher="icons"):
    t = open(path, encoding="utf-8").read()
    # Alt+Tab dialog: icons only (macOS-style) or the text list
    t = re.sub(r'(<action name="NextWindow">)(\s*<dialog>[^<]*</dialog>)?', lambda m: m.group(1) + "\n        <dialog>%s</dialog>" % switcher, t)
    t = re.sub(r"(<theme>\s*(?:<!--.*?-->\s*)?<name>)[^<]*(</name>)", r"\g<1>%s\2" % theme, t, flags=re.S)
    t = re.sub(r"<titleLayout>[^<]*</titleLayout>", "<titleLayout>CIMLN</titleLayout>", t)
    for place in ("ActiveWindow", "InactiveWindow"):
        t = re.sub(
            r'(<font place="%s">\s*<name>)[^<]*(</name>\s*<size>)\d+(</size>)' % place,
            r"\g<1>%s\g<2>%s\3" % (font, size),
            t,
        )
    open(path, "w", encoding="utf-8").write(t)


def add_keybind(path, key, command):
    """add <keybind key=KEY> running COMMAND to rc.xml unless it is already bound to that key"""
    t = open(path, encoding="utf-8").read()
    # replace an existing binding for this key so a changed command takes effect
    t = re.sub(r'  <keybind key="%s">.*?</keybind>\n' % re.escape(key), "", t, flags=re.S)
    block = ('  <keybind key="%s">\n    <action name="Execute">\n      <command>%s</command>\n'
             '    </action>\n  </keybind>\n') % (key, command)
    t = t.replace("</keyboard>", block + "  </keyboard>", 1)
    open(path, "w", encoding="utf-8").write(t)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "keybind":
        add_keybind(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(0)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    patch(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "10",
          sys.argv[4] if len(sys.argv) > 4 else "Inter", sys.argv[5] if len(sys.argv) > 5 else "icons")
