#!/usr/bin/env python3
"""Patch an Openbox rc.xml: theme name, title-bar button layout, window title font size.

usage: openbox_rc.py RC_XML THEME_NAME [FONT_SIZE] [FONT_FAMILY]
"""
import re
import sys


def patch(path, theme, size, font="Inter"):
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"(<theme>\s*(?:<!--.*?-->\s*)?<name>)[^<]*(</name>)", r"\g<1>%s\2" % theme, t, flags=re.S)
    t = re.sub(r"<titleLayout>[^<]*</titleLayout>", "<titleLayout>CIMLN</titleLayout>", t)
    for place in ("ActiveWindow", "InactiveWindow"):
        t = re.sub(
            r'(<font place="%s">\s*<name>)[^<]*(</name>\s*<size>)\d+(</size>)' % place,
            r"\g<1>%s\g<2>%s\3" % (font, size),
            t,
        )
    open(path, "w", encoding="utf-8").write(t)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    patch(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "10", sys.argv[4] if len(sys.argv) > 4 else "Inter")
