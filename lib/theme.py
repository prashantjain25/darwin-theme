#!/usr/bin/env python3
"""Theme configuration engine for golden-gate-lxqt-theme.

  theme.py env                     print shell variables (eval-able) for the resolved config
  theme.py get a.b.c               print one value
  theme.py transform SRC DST       copy a text asset applying palette/accent/radius/rim options
  theme.py openbox-border FILE     apply the window border options to an Openbox themerc
  theme.py configure               interactive wizard, writes config/theme.json
  theme.py validate                check the user config, exit 1 on problems

The user edits config/theme.json (created from config/theme.default.json); only
options that really need a human decision are exposed.
"""
import copy
import json
import os
import re
import shlex
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "config", "theme.default.json")
USER = os.environ.get("THEME_CONFIG", os.path.join(ROOT, "config", "theme.json"))

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load():
    cfg = json.load(open(DEFAULT, encoding="utf-8"))
    if os.path.exists(USER):
        cfg = deep_merge(cfg, json.load(open(USER, encoding="utf-8")))
    return cfg


def palette(cfg):
    name = "light" if cfg["mode"] == "light" else "dark"
    return json.load(open(os.path.join(ROOT, "palettes", name + ".json"), encoding="utf-8"))


def mix(alpha, base_rgb, bg):
    """composite a solid colour of `base_rgb` at `alpha` over grey `bg`"""
    return "#%02x%02x%02x" % tuple(round((1 - alpha) * bg + alpha * c) for c in base_rgb)


def resolve(cfg):
    pal = palette(cfg)
    light = cfg["mode"] == "light"
    accent = cfg["accent"] if cfg["accent"] != "auto" else pal["accent"]
    base = tuple(pal["alpha_base"])
    surface = 242 if light else 20  # window surface grey, for border compositing
    b = cfg["window"]["border"]
    width = int(b["width"]) if b["enabled"] else 0
    act = b["active_color"] if b["active_color"] != "auto" else mix(0.23, base, surface)
    ina = b["inactive_color"] if b["inactive_color"] != "auto" else mix(0.14, base, surface)
    return {
        "MODE": cfg["mode"],
        "ACCENT": accent,
        "ICON_THEME": pal["icon_theme"],
        "GTK_SOURCE": pal["gtk_source"],
        "BORDER_WIDTH": width,
        "BORDER_ACTIVE": act,
        "BORDER_INACTIVE": ina,
        "WIN_R": cfg["window"]["corner_radius"],
        "TB_FONT": cfg["window"]["titlebar_font_size"],
        "MENU_R": cfg["menu"]["corner_radius"],
        "MENU_RIM": int(bool(cfg["menu"]["rim"])),
        "FONT_UI": cfg["fonts"]["ui"],
        "FONT_SIZE": cfg["fonts"]["ui_size"],
        "FONT_MONO": cfg["fonts"]["mono"],
        "BAR_ENABLED": int(bool(cfg["menubar"]["enabled"])),
        "BAR_H": cfg["menubar"]["height"],
        "CLOCK_FORMAT": cfg["menubar"]["clock_format"],
        "DOCK_ENABLED": int(bool(cfg["dock"]["enabled"])),
        "DOCK_ICON": cfg["dock"]["icon_size"],
        "DOCK_W": cfg["dock"]["width"],
        "DOCK_APPS": " ".join(cfg["dock"]["apps"]),
    }


# ----------------------------------------------------------------- transform
def remove_rim(text):
    # GTK css block, QSS block, Kvantum svg element
    text = re.sub(r"/\* [^*]*glass rim[^*]*\*/\n[^{]*\{[^}]*\}\n?", "", text)
    text = re.sub(r"<(?:svg:)?rect[^>]*id=\"menu-rim\"[^>]*/>", "", text)
    return text


def transform(text, cfg):
    r = resolve(cfg)
    pal = palette(cfg)
    hexmap = {k.lower(): v for k, v in pal["hex"].items()}
    # one pass: dark -> light (identity for dark)
    if hexmap:
        text = HEX.sub(lambda m: hexmap.get(m.group(0).lower(), m.group(0)), text)
    # white-alpha tints -> black-alpha tints in light mode
    br, bg, bb = pal["alpha_base"]
    if (br, bg, bb) != (255, 255, 255):
        text = re.sub(r"rgba\(\s*255\s*,\s*255\s*,\s*255\s*,", "rgba(%d, %d, %d," % (br, bg, bb), text)
    # accent
    if r["ACCENT"].lower() != "#0091ff":
        text = re.sub(r"#0091ff", r["ACCENT"], text, flags=re.I)
    # menu radius (CSS / QSS)
    text = text.replace("border-radius: 14px", "border-radius: %dpx" % r["MENU_R"])
    if not r["MENU_RIM"]:
        text = remove_rim(text)
    return text


def apply_border(text, cfg):
    r = resolve(cfg)
    kv = {
        "border.width": str(r["BORDER_WIDTH"]),
        "window.active.border.color": r["BORDER_ACTIVE"],
        "window.inactive.border.color": r["BORDER_INACTIVE"],
    }
    for k, v in kv.items():
        pat = re.compile(r"^%s:.*$" % re.escape(k), re.M)
        text = pat.sub("%s: %s" % (k, v), text) if pat.search(text) else text.rstrip("\n") + "\n%s: %s\n" % (k, v)
    return text


# ----------------------------------------------------------------- validate
def validate(cfg):
    errs = []
    if cfg["mode"] not in ("dark", "light"):
        errs.append("mode must be 'dark' or 'light'")
    if cfg["accent"] != "auto" and not COLOR.match(cfg["accent"]):
        errs.append("accent must be 'auto' or #rrggbb")
    b = cfg["window"]["border"]
    for k in ("active_color", "inactive_color"):
        if b[k] != "auto" and not COLOR.match(b[k]):
            errs.append("window.border.%s must be 'auto' or #rrggbb" % k)
    if not (0 <= int(b["width"]) <= 4):
        errs.append("window.border.width must be 0..4")
    for k, lo, hi in (("corner_radius", 0, 40), ("titlebar_font_size", 8, 16)):
        if not (lo <= int(cfg["window"][k]) <= hi):
            errs.append("window.%s must be %d..%d" % (k, lo, hi))
    if not (0 <= int(cfg["menu"]["corner_radius"]) <= 30):
        errs.append("menu.corner_radius must be 0..30")
    if not (20 <= int(cfg["menubar"]["height"]) <= 60):
        errs.append("menubar.height must be 20..60")
    if not (16 <= int(cfg["dock"]["icon_size"]) <= 96):
        errs.append("dock.icon_size must be 16..96")
    return errs


# ----------------------------------------------------------------- wizard
def ask(prompt, default, cast=str, choices=None):
    while True:
        raw = input("%s [%s]: " % (prompt, default)).strip()
        if raw == "":
            return default
        try:
            val = cast(raw)
        except ValueError:
            print("  invalid value"); continue
        if choices and val not in choices:
            print("  choose one of: %s" % ", ".join(map(str, choices))); continue
        return val


def yesno(raw):
    if raw.lower() in ("y", "yes", "true", "1"):
        return True
    if raw.lower() in ("n", "no", "false", "0"):
        return False
    raise ValueError


def configure():
    cur = load()
    print("golden-gate-lxqt-theme configuration (Enter keeps the value in brackets)\n")
    cur["mode"] = ask("Mode (dark/light; light is experimental)", cur["mode"], str, ("dark", "light"))
    cur["accent"] = ask("Accent colour ('auto' or #rrggbb)", cur["accent"],
                        lambda s: s if s == "auto" or COLOR.match(s) else (_ for _ in ()).throw(ValueError))
    b = cur["window"]["border"]
    b["enabled"] = ask("Window border (yes/no)", "yes" if b["enabled"] else "no", yesno)
    if b["enabled"]:
        b["width"] = ask("  border width in px (1-4)", b["width"], int, range(1, 5))
        b["active_color"] = ask("  active border colour ('auto' or #rrggbb)", b["active_color"],
                                lambda s: s if s == "auto" or COLOR.match(s) else (_ for _ in ()).throw(ValueError))
        b["inactive_color"] = ask("  inactive border colour ('auto' or #rrggbb)", b["inactive_color"],
                                  lambda s: s if s == "auto" or COLOR.match(s) else (_ for _ in ()).throw(ValueError))
    cur["window"]["corner_radius"] = ask("Window corner radius (Figma: 17, 26 for toolbar windows)",
                                         cur["window"]["corner_radius"], int)
    cur["menu"]["rim"] = ask("Light rim on menus (yes/no)", "yes" if cur["menu"]["rim"] else "no", yesno)
    cur["fonts"]["ui_size"] = ask("UI font size in pt (Figma 13px = 10)", cur["fonts"]["ui_size"], int)
    cur["menubar"]["enabled"] = ask("Install menu bar (yes/no)", "yes" if cur["menubar"]["enabled"] else "no", yesno)
    cur["dock"]["enabled"] = ask("Install dock (yes/no)", "yes" if cur["dock"]["enabled"] else "no", yesno)
    if cur["dock"]["enabled"]:
        apps = ask("Dock apps in order, comma separated, "|" = separator (files,browser,ide,downloads,|,settings,trash)",
                   ",".join(cur["dock"]["apps"]))
        cur["dock"]["apps"] = [a.strip() for a in apps.split(",") if a.strip()]
    errs = validate(cur)
    if errs:
        print("\nNot saved:\n  " + "\n  ".join(errs)); sys.exit(1)
    # store only what differs from the defaults file's structure (keep full for readability)
    out = {k: v for k, v in cur.items() if not k.startswith("_")}
    os.makedirs(os.path.dirname(USER), exist_ok=True)
    json.dump(out, open(USER, "w", encoding="utf-8"), indent=2)
    print("\nSaved %s" % USER)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "env":
        for k, v in resolve(load()).items():
            print("%s=%s" % (k, shlex.quote(str(v))))
    elif cmd == "get":
        v = load()
        for part in sys.argv[2].split("."):
            v = v[part]
        print(v if not isinstance(v, bool) else str(v).lower())
    elif cmd == "transform":
        data = open(sys.argv[2], encoding="utf-8").read()
        open(sys.argv[3], "w", encoding="utf-8").write(transform(data, load()))
    elif cmd == "openbox-border":
        p = sys.argv[2]
        open(p, "w", encoding="utf-8").write(apply_border(open(p, encoding="utf-8").read(), load()))
    elif cmd == "configure":
        configure()
    elif cmd == "validate":
        errs = validate(load())
        for e in errs:
            print("config error:", e)
        sys.exit(1 if errs else 0)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
