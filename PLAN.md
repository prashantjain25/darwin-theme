# Plan: scripting the Golden Gate LXQt desktop

Goal: turn the hand-made desktop configuration into a repeatable, reversible installation that anyone on a
Lubuntu / LXQt system can apply, with the **desktop look** and the **menu bar + dock** as two separate parts.

Guiding aim: a familiar interface for macOS and Linux users, not a pixel copy of macOS.

## 1. Scope

| Part | Script | Covers |
|---|---|---|
| Desktop look | `install.sh` | fonts, fontconfig, Kvantum (Qt apps and PCManFM-Qt views), GTK theme, Openbox decoration, LXQt theme/fonts, picom, optional Lapce |
| Menu bar + dock | `dock.sh` | top panel (menu bar), bottom panel (dock), launchers, panel stylesheet blocks, picom rules for the dock |
| Undo | `restore.sh` | restores every file that the other two replaced, in reverse order |
| Manual choices | `config/theme.json`, `./install.sh --configure` | only options that need a human decision (mode, accent, window border, radii, menu rim, fonts, dock apps) |

## 2. Layout of the repository

```
install.sh  dock.sh  restore.sh
lib/        common.sh (log, deps, backup, restart)   theme.py (config, palette, wizard)
            panel.py (LXQt panel builder)   openbox_rc.py   ini.py   gtkdark.py
assets/     kvantum/ openbox/ lxqt/ gtk/ picom/ fontconfig/ lapce/ dock/ fonts/Inter/
config/     theme.default.json   (user copy: theme.json, ignored by git)
palettes/   dark.json  light.json (experimental)
docs/       FIGMA-DESIGN-SPEC.md
_resources/ screenshots used by the README
```

## 3. Design decisions

1. **Idempotent and reversible.** Every write goes through `backup`, which records `BAK <path>` (existing file
   saved) or `NEW <path>` (file did not exist). `restore.sh` replays the manifest backwards.
2. **Dependency detection first.** Each script checks commands, Qt styles, the LXQt theme, icon/GTK themes and
   fonts, prints the exact `apt` command for what is missing, and only installs with `--install-deps`. Nothing
   is installed silently, and sudo is only used for `apt-get`.
3. **Assets are the finished result, scripts do the personalisation.** Colour values stay in the assets; the
   JSON config is applied by a single transform (`theme.py transform`): palette swap (dark/light), accent,
   menu radius, rim on/off. Openbox border and picom radii are rendered from the config.
4. **Two independent elements.** `install.sh` never touches the panel layout; `dock.sh` never touches Qt/GTK.
   The panel stylesheet is composed from a base part (desktop) plus optional menu-bar and dock blocks, tracked
   in a small state file, so running either script later keeps the other part intact.
5. **No machine-specific paths.** Launchers for the dock are generated from what is installed (browser, file
   manager, settings, download manager, IDE); missing apps are skipped with a warning.
6. **Third-party code stays out unless the license allows it.** Inter (OFL 1.1) is bundled with its license;
   WhiteSur GTK/icon themes are fetched from upstream; Maple Mono is downloaded with a pinned checksum.

## 4. Steps

| # | Step | Status |
|---|---|---|
| 1 | Collect the final configuration files (Kvantum, Openbox, LXQt, picom, fontconfig, GTK CSS, Lapce) into `assets/` | done |
| 2 | Shared library: logging, dependency checks, backups, restart helpers | done |
| 3 | JSON configuration engine, palettes, validation, interactive wizard | done |
| 4 | `install.sh` with modules (`--only` / `--skip`, `--dry-run`, `--install-deps`) | done |
| 5 | `dock.sh`: launcher detection, panel layout, stylesheet blocks, picom rules | done |
| 6 | `restore.sh` | done |
| 7 | Bundle Inter with its OFL license and install it only when missing | done |
| 8 | README, third-party notices, screenshots | done |
| 9 | Tests in a throw-away `$HOME` (dry-run, real run, light mode, bad config, wizard, restore) | done |
| 9a | Native Qt/X11 glass switcher: selected app label, opaque icons, dependency/startup, reversible shortcuts; live keyboard tests | done |
| 10 | Re-extract measurements from Apple's macOS 27 Figma kit (adds a real Dark Mode) and update the assets | open |
| 11 | Verify light mode on screen, then drop the "experimental" label | open |
| 12 | Global menu: evaluate a host for LXQt (e.g. a vala-panel based applet) and the Qt/GTK exporters | open |
| 13 | Packaging (`.deb`) and publishing | open |

## 5. Testing approach

* Run every script against a temporary home (`HOME=/tmp/x`, with `GG_SKIP_GSETTINGS=1` and `--no-restart`) so the
  real session is untouched; check generated files, then `restore.sh all` and confirm they are removed.
* Render Qt menus and PCManFM-Qt on a virtual X screen (Xvfb) with the real Kvantum theme and measure sizes from pixels.
* Window decoration geometry is measured from a capture of the title bar (circle size, insets, gaps as a
  percentage of the 32 px title bar).

## 6. Known risks

* The panel rewrites its configuration when it exits, so `dock.sh` stops it before writing.
* Restart helpers act on the *running* session; tests must pass `--no-restart` (or set `GG_NO_RESTART=1`).
* Kvantum row height and rounded-corner shapes are limited by the style engine, see the README.
