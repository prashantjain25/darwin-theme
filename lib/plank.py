#!/usr/bin/env python3
"""Generate a Plank theme and pinned launchers that match the design kit's dock.

usage: plank.py --home DIR --mode dark|light --icon-size N [--fill #rrggbb] [--opacity N]
                [--border 0|1] [--ring 0|1] [--radius N] [--padding N] --app DESKTOP ...

Writes
  <home>/.local/share/plank/themes/GoldenGate/dock.theme
  <home>/.config/plank/dock1/launchers/NN-name.dockitem
and prints "key<TAB>gvariant" lines (dock settings) for the caller to apply with gsettings.

Plank theme paddings are "tenths of a percent of the icon size", so pixels are converted
with  value = px / icon_size * 10.  The design kit's dock: padding 8 px (sides), 10 px (top),
11 px (bottom), 9 px between items, fill and 1 px strokes as given in the arguments.
Dock behaviour (--dock-mode): reserve and always-on-top both map to hide-mode 'none' (Plank always
reserves its space then), intelligent-hide to 'intelligent', auto-hide to 'auto' with pressure reveal.
Not supported by Plank, and therefore ignored: the 5 px offset from the screen edge.
The separator is a do-nothing launcher whose icon is a 1 px line (added by dock.sh).
"""
import argparse
import os
import sys


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "%d;;%d;;%d;;%d" % (r, g, b, round(255 * alpha / 100))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=os.path.expanduser("~"))
    ap.add_argument("--mode", default="dark", choices=["dark", "light"])
    ap.add_argument("--icon-size", type=int, default=36)
    ap.add_argument("--fill", default="")
    ap.add_argument("--opacity", type=float, default=-1)
    ap.add_argument("--border", type=int, default=1)
    ap.add_argument("--ring", type=int, default=1)
    ap.add_argument("--radius", type=int, default=15)
    ap.add_argument("--padding", type=int, default=8)
    ap.add_argument("--top-pad", type=float, default=10)
    ap.add_argument("--bottom-pad", type=float, default=11)
    ap.add_argument("--item-gap", type=float, default=9)
    ap.add_argument("--dock-mode", default="reserve")
    ap.add_argument("--app", action="append", default=[])
    a = ap.parse_args()

    light = a.mode == "light"
    fill = a.fill or ("#f6f6f6" if light else "#4a4a4a")
    opacity = a.opacity if a.opacity >= 0 else (36 if light else 39)
    # dark theme: rims are white tints, never black (see the theme's border rule)
    inner = rgba("#1a1a1a", 46) if (a.border and light) else rgba("#ffffff", 16) if a.border else rgba(fill, opacity)
    outer = rgba("#000000", 15) if (a.ring and light) else rgba("#ffffff", 8) if a.ring else rgba(fill, 0)

    def tenths(px):
        return round(px / a.icon_size * 10, 3)

    theme_dir = os.path.join(a.home, ".local/share/plank/themes/GoldenGate")
    os.makedirs(theme_dir, exist_ok=True)
    theme = f"""[PlankTheme]
TopRoundness={a.radius}
BottomRoundness={a.radius}
LineWidth={1 if (a.border or a.ring) else 0}
OuterStrokeColor={outer}
FillStartColor={rgba(fill, opacity)}
FillEndColor={rgba(fill, opacity)}
InnerStrokeColor={inner}

[PlankDockTheme]
HorizPadding={tenths(a.padding)}
TopPadding={tenths(a.top_pad)}
BottomPadding={tenths(a.bottom_pad)}
ItemPadding={tenths(a.item_gap)}
IndicatorSize=5
IconShadowSize=0
UrgentBounceHeight=1.6666666666666667
LaunchBounceHeight=0
FadeOpacity=1
ClickTime=300
UrgentBounceTime=600
LaunchBounceTime=600
ActiveTime=300
SlideTime=300
FadeTime=250
HideTime=250
GlowSize=0
GlowTime=10000
GlowPulseTime=2000
UrgentHueShift=150
ItemMoveTime=450
CascadeHide=true
BadgeColor=0;;0;;0;;0
"""
    open(os.path.join(theme_dir, "dock.theme"), "w", encoding="utf-8").write(theme)

    launch_dir = os.path.join(a.home, ".config/plank/dock1/launchers")
    os.makedirs(launch_dir, exist_ok=True)
    for f in os.listdir(launch_dir):
        if f.endswith(".dockitem") and f.startswith("gg-"):
            os.remove(os.path.join(launch_dir, f))
    items = []
    for i, desk in enumerate(a.app, 1):
        name = "gg-%02d-%s.dockitem" % (i, os.path.splitext(os.path.basename(desk))[0].replace("golden-gate-dock-", ""))
        with open(os.path.join(launch_dir, name), "w", encoding="utf-8") as fh:
            fh.write("[PlankDockItemPreferences]\nLauncher=file://%s\n" % desk)
        items.append(name)

    # dock settings for gsettings (relocatable schema net.launchpad.plank.dock.settings at dock1)
    hide = {"reserve": "none", "always-on-top": "none", "intelligent-hide": "intelligent", "auto-hide": "auto"}[a.dock_mode]
    out = {
        "theme": "'GoldenGate'",
        "icon-size": str(a.icon_size),
        "position": "'bottom'",
        "alignment": "'center'",
        "items-alignment": "'center'",
        "hide-mode": "'%s'" % hide,
        "pressure-reveal": "true" if a.dock_mode == "auto-hide" else "false",
        "zoom-enabled": "true",
        "zoom-percent": "1.5",
        "pinned-only": "true",
        "lock-items": "true",
        "tooltips-enabled": "true",
        "show-dock-item": "false",
        "dock-items": "[%s]" % ", ".join("'%s'" % i for i in items),
    }
    for k, v in out.items():
        print("%s\t%s" % (k, v))


if __name__ == "__main__":
    sys.exit(main())
