# Golden Gate LXQt Theme

A macOS-inspired theme for **LXQt / Lubuntu**, with a top menu bar, bottom dock,
traffic-light window controls, translucent menus and an Alt+Tab window switcher.

| Menu bar | Dock |
|---|---|
| ![Menu bar](_resources/menubar.png) | ![Dock](_resources/dock.png) |

| Window controls | Menus |
|---|---|
| ![Window controls](_resources/titlebar.png) | ![Menus](_resources/menu.png) |

![File manager](_resources/filemanager.png)

Dock zoom (the icon under the pointer grows, as on macOS):

![Dock zoom](_resources/dock-zoom.gif)

## Features

- Dark themes for Qt and GTK applications.
- Rounded windows, shadows and blurred backgrounds.
- Traffic-light window controls and thin window borders.
- A top panel with an application launcher, system tray and clock.
- A dock with shortcuts to your applications.
- An Alt+Tab switcher that shows one icon per window, with the selected name below it.
- Inter for interface text and Maple Mono NF for monospace text.

## Requirements

Tested on **Lubuntu 26.04** (LXQt 2.3, Qt 6, Openbox 3.6, picom 12.5).
The window switcher and the launcher need an X11 session.

Install every package the scripts use with one command:

```bash
sudo apt install \
  lxqt lxqt-themes openbox picom pcmanfm-qt \
  qt5-style-kvantum qt6-style-kvantum \
  fonts-inter rofi qalc plocate plank \
  python3 curl unzip git fontconfig x11-utils x11-xserver-utils xdg-utils \
  libglib2.0-bin libglib2.0-dev-bin libgtk-3-bin
```

What each group provides:

| Group | Used for |
|---|---|
| `lxqt`, `lxqt-themes`, `pcmanfm-qt` | the desktop, panels, file manager and the `sombre-et-rond` theme |
| `openbox`, `picom` | window decoration, shortcuts and window effects |
| `qt5-style-kvantum`, `qt6-style-kvantum` | Qt app appearance (Kvantum) |
| `fonts-inter` | interface font |
| `rofi`, `qalc`, `plocate` | Spotlight-style launcher: apps, calculator and currency, file search |
| `plank` | the dock, with icon zoom |
| `python3`, `python3-pyqt6` | installer scripts, and the window switcher's PyQt6 dialog |
| `curl`, `unzip`, `git`, `fontconfig` | downloads, font setup and cloning the WhiteSur themes |
| `x11-utils`, `x11-xserver-utils` | `xprop`, `xwininfo`, `xrandr`, `setxkbmap`, `xmodmap` |
| `xdg-utils` | `xdg-open` for file search results |
| `libglib2.0-bin`, `libglib2.0-dev-bin`, `libgtk-3-bin` | GTK theme build and `gsettings` |

Also needed for the GTK theme and icons (installed by `--install-deps`, or by hand):

- [WhiteSur GTK theme](https://github.com/vinceliuice/WhiteSur-gtk-theme)
- [WhiteSur icon theme](https://github.com/vinceliuice/WhiteSur-icon-theme)

The installer checks these and tells you what is missing. Check the packages after installing with `./install.sh --dry-run`.

## Install

Run these commands from the project directory:

```bash
./install.sh --install-deps
./dock.sh
```

The first command installs the desktop theme and missing dependencies. The second
sets up the menu bar and dock. You can use either separately.

Log out and back in after installation. Restart open applications to apply their
new appearance.

To preview the changes before installing:

```bash
./install.sh --dry-run
./dock.sh --dry-run
```

Existing settings are backed up before they are replaced. To undo the last run:

```bash
./restore.sh
```

Use `./restore.sh all` to undo all installations.

## Settings

Run `./install.sh --configure` to choose your settings, or edit
`config/theme.json`. See `config/theme.default.json` for the available options.

| Setting | Default | Description |
|---|---|---|
| `mode` | `dark` | `dark` or `light`; light mode is experimental |
| `accent` | `auto` | Default accent color, or a color such as `#0088ff` |
| `window.border.enabled` | `true` | Show window borders |
| `window.border.width` | `1` | Border width in pixels |
| `window.corner_radius` | `17` | Window corner radius in pixels |
| `menu.corner_radius` | `14` | Menu corner radius in pixels |
| `fonts.ui` | `Inter` | Interface font |
| `fonts.ui_size` | `10` | Interface font size in points |
| `fonts.mono` | `Maple Mono NF` | Monospace font |
| `switcher.style` | `icons` | Icon switcher or Openbox's `list` view |
| `switcher.opacity` | `67` | Background opacity, from 30 to 100; icons and text stay opaque |
| `dock.backend` | `plank` | `plank` (icon zoom) or `lxqt-panel` (simpler, no zoom) |
| `dock.icon_size` | `36` | Dock icon size in pixels |
| `dock.apps` | See defaults | Applications shown in the dock |

Run `./install.sh` or `./dock.sh` again after changing the relevant settings.

To apply just the window switcher and its appearance:

```bash
./install.sh --only switcher,picom
```

Use `--only kvantum,gtk` to apply only the application themes, or `--skip fonts`
to leave fonts alone. Both scripts accept `--no-restart` to apply settings without
restarting desktop components. Run either script with `--help` for all options.

## Window switcher

Hold Alt and press Tab to move between windows. Alt+Shift+Tab moves backward.
Release Alt to select a window, or press Escape to cancel.

The switcher is Openbox's icon dialog. It shows one icon per window, with the
selected window's name below. `switcher.style` in `config/theme.json` can be set to
`list` for the text list instead.

## Dock

Run `./dock.sh --dock-only` to set up just the dock, or `--menubar-only` for just
the top panel.

The dock uses [Plank](https://launchpad.net/plank). Icons grow smoothly under the
pointer. The dock is sized from your screen resolution (`dock.scale`, `auto` by
default), and it hides until the pointer reaches the bottom edge.

The separator between the apps and the folders and trash is a thin line. It takes
the width of one icon, so the gap next to it is wider than the gaps between icons.

Change the dock's behavior with:

```bash
./dock.sh --dock-mode auto-hide
```

Other modes are `reserve` (the full bottom edge is reserved), `always-on-top`
and `intelligent-hide`. The LXQt panel does not respond to window overlap, so
`intelligent-hide` behaves like `auto-hide` here.

## Limitations

- Application menus such as File and Edit stay inside their windows. LXQt has no
  global menu host, and the Qt and GTK menu exporters need a registrar that is not
  packaged for this release.
- Menu spacing can differ between Qt and GTK applications.
- The dock has no blur behind it. Plank can only blur its whole window, which
  would also blur the empty strip across the bottom of the screen.
- If the file manager opens a blank window after a desktop restart, log out and back in.

## License and credits

Scripts and configuration are licensed under MIT; see [LICENSE](LICENSE).
Third-party themes and fonts have their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).
WhiteSur is by vinceliuice.

macOS and Golden Gate are Apple trademarks. This project is not affiliated with
or endorsed by Apple.
