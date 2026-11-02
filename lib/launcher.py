#!/usr/bin/env python3
"""Render the Spotlight-style launcher theme so its size follows the user's screen.

Each Figma value (Search Field, macOS 26 kit) is kept as a percentage of the Figma frame
(1512 x 982 pt). Pixels on this display are percentage x screen size:
  widths and horizontal padding  -> % of screen width
  heights, radius and font size  -> % of screen height
usage: launcher.py TEMPLATE OUTPUT [WIDTH HEIGHT]   (WIDTH/HEIGHT default: primary xrandr output)
"""
import re
import subprocess
import sys

REF_W, REF_H = 1512, 982                      # Figma kit frame, pt
WINDOW_W_PCT = 25                             # not from Figma: launcher width as % of screen width
FIELD_W, FIELD_H = 120, 24                    # Search Field component
PCT = {
    "radius":    6 / REF_H * 100,            # corner radius (height based)
    "pad_left":  8 / REF_W * 100,
    "pad_right": 4 / REF_W * 100,
    "gap":       2 / REF_W * 100,
    "pad_v":     4 / REF_H * 100,            # (24 - 16) / 2 px
    "icon":      16 / REF_H * 100,
    "field_h":   FIELD_H / REF_H * 100,
    "font":      13 / REF_H * 100,            # SF 13 px = Inter 10 pt
}


def screen_size():
    out = subprocess.run(["xrandr"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+)x(\d+)\+\d+\+\d+", next((l for l in out.splitlines() if " connected primary" in l), ""))
    return (int(m.group(1)), int(m.group(2))) if m else (REF_W, REF_H)


def main():
    tpl, out = sys.argv[1], sys.argv[2]
    w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else screen_size()
    # one uniform scale for every metric (screen width / Figma frame width), as the dock uses,
    # so proportions stay the same on any aspect ratio
    s = w / REF_W
    px = lambda key, axis: round(PCT[key] / 100 * REF_W * s)
    font_pt = round(13 * s * 72 / 96)               # SF 13 px at this scale -> pt (96 dpi)
    win_w = round(WINDOW_W_PCT / 100 * w)           # not in Figma: window width as % of screen width
    vals = {
        "@SPOT_WIDTH@": win_w,
        "@SPOT_RADIUS@": px("radius", "h"),
        "@SPOT_PAD_L@": px("pad_left", "w"),
        "@SPOT_PAD_R@": px("pad_right", "w"),
        "@SPOT_GAP@": px("gap", "w"),
        "@SPOT_ICON@": px("icon", "h"),
        "@SPOT_PAD_V@": px("pad_v", "h"),
        "@SPOT_FONT_PT@": font_pt,
    }
    t = open(tpl, encoding="utf-8").read()
    for k, v in vals.items():
        t = t.replace(k, str(v))
    open(out, "w", encoding="utf-8").write(t)
    print("launcher theme for %dx%d: %s" % (w, h, ", ".join("%s=%s" % (k.strip("@"), v) for k, v in vals.items())))


if __name__ == "__main__":
    main()
