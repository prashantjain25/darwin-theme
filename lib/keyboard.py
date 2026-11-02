#!/usr/bin/env python3
"""Pick launcher shortcuts from the keyboard that is actually connected.

usage: keyboard.py modifier    -> Openbox modifier prefix: always "W" (Windows/Super key)
       keyboard.py describe    -> one line describing what was detected
Detection reads the X keyboard map: xmodmap -pm lists the keys bound to Mod4 (Super).
"""
import subprocess
import sys


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def detect():
    query = run(["setxkbmap", "-query"])
    model = next((l.split(":", 1)[1].strip() for l in query.splitlines() if l.startswith("model:")), "")
    mods = run(["xmodmap", "-pm"])
    mod4 = next((l for l in mods.splitlines() if l.lower().startswith("mod4")), "")
    has_super = any(k in mod4 for k in ("Super", "Meta", "Hyper", "Super_L", "Super_R", "Meta_L", "Meta_R"))
    apple = model.lower().startswith(("apple", "macintosh", "mac"))
    return model or "unknown", has_super, apple


if __name__ == "__main__":
    model, has_super, apple = detect()
    if sys.argv[1:] == ["modifier"]:
        print("W")   # the Windows/Super key is always used for the launcher shortcuts
    elif sys.argv[1:] == ["describe"]:
        kind = "Apple (Command key)" if apple else ("Windows/Linux (Super key)" if has_super else "no Super key")
        print("%s, model %s" % (kind, model))
    else:
        sys.exit(__doc__)
