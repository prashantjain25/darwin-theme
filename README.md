# Golden Gate LXQt Theme

A dark, Figma-measured desktop theme for **LXQt / Lubuntu** that gives people coming from macOS a familiar
interface on Linux: a menu bar on top, a dock at the bottom, traffic-light window controls,
rounded translucent menus and a clean file manager.

> **The aim is not to copy macOS.** It is to offer a **familiar interface for Linux and macOS
> users**: the same places for the same things (menu bar, dock, window controls, menus, file
> manager). People coming from a Mac should not have to relearn where everything is, and
> Linux users get a consistent, polished desktop. The theme only borrows *layout conventions and
> proportions* (measured from Apple's public design resources); it ships no Apple assets.

| Menu bar | Dock |
|---|---|
| ![menu bar](_resources/menubar.png) | ![dock](_resources/dock.png) |

| Window controls | Menus |
|---|---|
| ![title bar](_resources/titlebar.png) | ![menu](_resources/menu.png) |

![file manager](_resources/filemanager.png)

*(Screenshots are taken from a real session / a virtual screen with demo files.)*

## What you get

| Piece | What it does | Installed by |
|---|---|---|
| **Qt apps (Kvantum)** | dark surfaces, rounded accent highlights, tick marks instead of check boxes, glass menu with light rim, PCManFM-Qt list stripes / dimmed header / dark location bar | `install.sh` |
| **GTK apps** | `WhiteSur-Dark-Black` (built from WhiteSur-Dark with a darker palette), menu rim, tick marks | `install.sh` |
| **Window decoration (Openbox)** | 32/33 px title bar, 14 px traffic lights at the Figma positions, light 1 px border | `install.sh` |
| **LXQt theme + fonts** | icon theme, UI font Inter 10 pt, monospace Maple Mono NF | `install.sh` |
| **picom** | rounded windows (17 px), menus (14 px), shadows, blur | `install.sh` |
| **Lapce** (optional) | matching sizes and fonts, true 1.0 UI scale | `install.sh` |
| **Menu bar** | 34 px top panel: start icon, tray, one-line clock | `dock.sh` |
| **Dock** | 6 pinned apps: files (PCManFM-Qt), browser, settings, trash, download manager, IDE | `dock.sh` |

The desktop look (`install.sh`) and the menu bar + dock (`dock.sh`) are **separate elements**; use either or both.

## Requirements

Tested on **Lubuntu 26.04** (LXQt 2.3, Qt 6, Openbox 3.6, picom 12.5). Debian/Ubuntu-family package names:

| Need | Package / source |
|---|---|
| LXQt session with Openbox, panel, file manager | `lxqt`, `openbox`, `lxqt-panel`, `pcmanfm-qt`, `lxqt-themes` |
| Compositor | `picom` |
| Qt style | `qt5-style-kvantum`, `qt6-style-kvantum` (and optionally `qt5-style-kvantum-themes`) |
| Build tools used by the scripts | `python3`, `curl`, `unzip`, `git`, `fontconfig`, `x11-utils`, `libglib2.0-bin`, `libglib2.0-dev-bin`, `libgtk-3-bin` |
| **WhiteSur GTK theme** (base for `WhiteSur-Dark-Black`) | [vinceliuice/WhiteSur-gtk-theme](https://github.com/vinceliuice/WhiteSur-gtk-theme) |
| **WhiteSur icon theme** (dock icons, UI icons) | [vinceliuice/WhiteSur-icon-theme](https://github.com/vinceliuice/WhiteSur-icon-theme) |
| UI font **Inter** | **bundled** (SIL OFL 1.1), installed automatically if missing |
| Mono font **Maple Mono NF** | downloaded (checksum-verified) by `install.sh` |

The scripts **detect what is missing** and tell you the exact command. Add `--install-deps` to let them do it
(`sudo apt install …`, plus cloning and installing the two WhiteSur themes into your home directory).

### Installing the WhiteSur dependencies by hand

```bash
# GTK theme (installs into ~/.themes; use -c Light as well if you want the experimental light mode)
git clone --depth 1 https://github.com/vinceliuice/WhiteSur-gtk-theme.git
(cd WhiteSur-gtk-theme && ./install.sh -c Dark -o normal)

# Icon theme (installs into ~/.local/share/icons: WhiteSur, WhiteSur-light, WhiteSur-dark)
git clone --depth 1 https://github.com/vinceliuice/WhiteSur-icon-theme.git
(cd WhiteSur-icon-theme && ./install.sh)

# Qt style + build tools
sudo apt install qt5-style-kvantum qt6-style-kvantum picom openbox lxqt-themes \
                 libglib2.0-bin libglib2.0-dev-bin libgtk-3-bin x11-utils python3 curl unzip git
```

## Install

```bash
git clone <this repo> golden-gate-lxqt-theme && cd golden-gate-lxqt-theme

./install.sh --dry-run            # see what would happen (nothing is changed)
./install.sh --install-deps       # desktop look: Qt, GTK, Openbox, LXQt, picom, fonts, Lapce
./dock.sh                         # menu bar + dock (separate element)
```

Log out and back in once so every Qt/GTK app picks up the new styling. Every file that is replaced is
backed up first: undo everything with `./restore.sh all` (or just the last run with `./restore.sh`).

Useful flags: `--only kvantum,gtk` / `--skip lapce` (modules: `fonts fontconfig kvantum gtk openbox lxqt picom pcmanfm lapce`),
`--no-restart`, `-y`, `--pcmanfm-detailed`. Dock: `--menubar-only`, `--dock-only`.

## Configuration (for the things that need a human decision)

Only options that really need a person's choice are exposed. They live in **`config/theme.json`**
(copy `config/theme.default.json`, or let the wizard write it):

```bash
./install.sh --configure     # interactive: mode, accent, window border, radius, menu rim, fonts, dock apps
python3 lib/theme.py validate
```

| Key | Default | Meaning |
|---|---|---|
| `mode` | `dark` | `dark` or `light` (**light is experimental**, palette derived from Figma light values, not verified) |
| `accent` | `auto` | `auto` (Figma accent for the mode) or `#rrggbb` |
| `window.border.enabled / width` | `true / 1` | window border; width `0` makes the title bar exactly 32 px, with a border Openbox makes it 33 px |
| `window.border.active_color / inactive_color` | `auto` | `auto` = white 23 % / 14 % in dark mode, black in light mode, or `#rrggbb` |
| `window.corner_radius` | `17` | picom radius (Figma 16 + squircle correction; 26 for toolbar-style windows) |
| `window.titlebar_font_size` | `10` | pt |
| `menu.rim` / `menu.corner_radius` | `true / 14` | thin light edge on menus / radius |
| `fonts.ui`, `fonts.ui_size`, `fonts.mono` | `Inter`, `10`, `Maple Mono NF` | Figma text is 13 px = Inter 10 pt |
| `menubar.enabled / height / clock_format` | `true / 34 / "ddd MMM d  h:mm AP"` | menu bar |
| `dock.enabled / icon_size / width / apps / custom` | `true / 36 / auto / [...]` | apps: `files browser settings trash downloads ide`; `custom` takes `{"name","exec","icon"}` |

Re-run `./install.sh` / `./dock.sh` after editing. Dark/light borders are deliberately configurable:
a *dark* border on a dark theme does not read as an outline, so the default is a light hairline.

## How it works

`lib/common.sh` (logging, dependency detection, backups), `lib/theme.py` (JSON config, palette transform,
wizard), `lib/panel.py` (LXQt panel layout), `lib/gtkdark.py` (darkens the compiled WhiteSur GTK resources),
`assets/` (Kvantum theme, Openbox theme + generated traffic-light bitmaps, panel stylesheets, picom template).
The design values come from Apple's public Figma kit; see [`docs/FIGMA-DESIGN-SPEC.md`](docs/FIGMA-DESIGN-SPEC.md)
and [`PLAN.md`](PLAN.md).

## Known limitations

- **No global menu**: LXQt's panel has no host for the focused app's File/Edit menus, so they stay inside windows.
- Qt cannot dim secondary list columns, and Kvantum rows are ~24 px (Figma list: 20 px); highlights are rounded
  ~5 × 3 px (a full 8 px radius would make menu rows 32 px).
- The Figma *dark* values are derived (the community macOS 26 file has no resolved dark mode). Apple's macOS 27
  ("Golden Gate") kit adds Dark Mode: <https://www.figma.com/community/file/1651309434229735362/macos-27>.
- If a PCManFM-Qt window opened by a restarted desktop process is blank, log out and back in.

## Licenses and credits

Scripts and configuration: MIT (see `LICENSE`). Bundled and derived third-party material, including
**Inter (SIL OFL 1.1)** and the GPL-3.0-derived Kvantum theme, is listed in [`THIRD_PARTY.md`](THIRD_PARTY.md).
"macOS" and "Golden Gate" are Apple trademarks / product names; this project is not affiliated with or
endorsed by Apple. WhiteSur is by vinceliuice.
