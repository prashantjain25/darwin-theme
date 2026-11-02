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

## Features

- Dark themes for Qt and GTK applications.
- Rounded windows, shadows and blurred backgrounds.
- Traffic-light window controls and thin window borders.
- A top panel with an application launcher, system tray and clock.
- A dock with shortcuts to your applications.
- An Alt+Tab switcher with large icons and the selected application's name.
- Inter for interface text and Maple Mono NF for monospace text.

## Requirements

Tested on **Lubuntu 26.04**, with LXQt 2.3, Qt 6, Openbox 3.6 and picom 12.5.
The window switcher requires an X11 session.

| Component | Package or source |
|---|---|
| Desktop | `lxqt`, `openbox`, `lxqt-panel`, `pcmanfm-qt`, `lxqt-themes` |
| Window effects | `picom` 12 or later |
| Qt appearance | `qt5-style-kvantum`, `qt6-style-kvantum` |
| Window switcher | `python3-pyqt6`, `libx11-6` |
| Optional dock | `plank` |
| Installation tools | `python3`, `curl`, `unzip`, `git`, `fontconfig`, `x11-utils`, `libglib2.0-bin`, `libglib2.0-dev-bin`, `libgtk-3-bin` |
| GTK theme | [WhiteSur GTK](https://github.com/vinceliuice/WhiteSur-gtk-theme) |
| Icons | [WhiteSur icons](https://github.com/vinceliuice/WhiteSur-icon-theme) |
| Inter | Included |
| Maple Mono NF | Installed automatically |

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
| `dock.backend` | `lxqt-panel` | Use the LXQt panel or `plank` for the dock |
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

The switcher shows windows from all desktops. Its background is translucent and
blurred; icons and text remain opaque.

## Dock

Run `./dock.sh --dock-only` to set up just the dock, or `--menubar-only` for just
the top panel.

For a translucent dock background with opaque icons, set `dock.backend` to
`plank`, install Plank, and run `./dock.sh --dock-only` again.

Change the dock's behavior with:

```bash
./dock.sh --dock-mode auto-hide
```

Other modes are `reserve`, `always-on-top` and `intelligent-hide`.
Plank does not support the separator or the gap below the dock.

## Limitations

- Application menus such as File and Edit stay inside their windows.
- Menu spacing can differ between Qt and GTK applications.
- If the file manager opens a blank window after a desktop restart, log out and back in.

## License and credits

Scripts and configuration are licensed under MIT; see [LICENSE](LICENSE).
Third-party themes and fonts have their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).
WhiteSur is by vinceliuice.

macOS and Golden Gate are Apple trademarks. This project is not affiliated with
or endorsed by Apple.
