#!/usr/bin/env python3
"""Minimal, order-preserving INI/Qt-settings editor.

usage: ini.py FILE SECTION KEY=VALUE [KEY=VALUE ...]

Creates the file/section if missing and only touches the given keys. Values are
written verbatim (quotes are kept), so Qt-style values such as
font="Inter,10,-1,5,50,0,0,0,0,0" work unchanged.
"""
import os
import re
import sys


def set_keys(path, section, pairs):
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        if lines and lines[-1] == "":
            lines.pop()

    header = "[%s]" % section
    start = next((i for i, l in enumerate(lines) if l.strip() == header), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(header)
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))

    for key, value in pairs:
        pat = re.compile(r"^%s\s*=" % re.escape(key))
        idx = next((i for i in range(start + 1, end) if pat.match(lines[i])), None)
        new = "%s=%s" % (key, value)
        if idx is None:
            ins = end
            while ins > start + 1 and lines[ins - 1].strip() == "":   # keep the blank line that separates sections
                ins -= 1
            lines.insert(ins, new)
            end += 1
        else:
            lines[idx] = new

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    kv = []
    for a in sys.argv[3:]:
        k, _, v = a.partition("=")
        kv.append((k, v))
    set_keys(sys.argv[1], sys.argv[2], kv)
