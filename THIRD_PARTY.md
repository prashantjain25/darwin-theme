# Third-party material

| Component | How it is used here | License | Notes |
|---|---|---|---|
| **Inter** typeface ([rsms/inter](https://github.com/rsms/inter)) | **Bundled** unmodified in `assets/fonts/Inter/` (variable TTFs + `OFL.txt` + `README.txt`); installed to `~/.local/share/fonts/Inter` only if no Inter is present | SIL Open Font License 1.1, © 2020 The Inter Project Authors | "Inter" is a Reserved Font Name: the font files must not be modified and redistributed under that name. The OFL text must stay with the font files (the installer copies `OFL.txt` along). The font may not be sold by itself. |
| **Maple Mono NF** ([subframe7536/maple-font](https://github.com/subframe7536/maple-font)) | **Downloaded** by `install.sh` from the upstream release (v7.9, SHA-256 pinned); not bundled | SIL Open Font License 1.1 | Optional monospace font (`fonts.mono`). |
| **WhiteSur Kvantum theme** ([vinceliuice/WhiteSur-kde](https://github.com/vinceliuice/WhiteSur-kde)) | `assets/kvantum/WhiteSurDark/` is a **modified derivative** (darker palette, rounded highlights, glass menu, tick marks) | GPL-3.0 | This derivative stays under **GPL-3.0**. |
| **WhiteSur GTK theme** ([vinceliuice/WhiteSur-gtk-theme](https://github.com/vinceliuice/WhiteSur-gtk-theme)) | **Not bundled.** Installed by the user; `install.sh` reads it and writes a darkened copy (`WhiteSur-Dark-Black`) into `~/.themes` | MIT | The generated copy is local to the user's machine. |
| **WhiteSur icon theme** ([vinceliuice/WhiteSur-icon-theme](https://github.com/vinceliuice/WhiteSur-icon-theme)) | **Not bundled.** Installed by the user; referenced by name and by file path (dock icons) | GPL-3.0 | |
| **LXQt theme "sombre-et-rond"** | **Not bundled.** Copied from `/usr/share/lxqt/themes` at install time, then our stylesheet is applied | LXQt themes (LGPL/GPL as shipped by `lxqt-themes`) | |
| **Openbox theme "OpenboxSur-Dark-Custom"** | `assets/openbox/`: `themerc` colours and the generated traffic-light bitmaps (`*.xbm`, produced by a script from circles and glyphs) | MIT (this project) | |
| **Apple design resources** (Figma community kits for macOS 26 / 27) | **Not bundled.** Only measurements (sizes, radii, spacing, colours) were read from the public kit and are documented in `docs/FIGMA-DESIGN-SPEC.md` | Apple's license terms for the design resources | No Apple artwork, icons or fonts (SF Pro) are included. |

If you redistribute this repository, keep `assets/fonts/Inter/OFL.txt`, this file and `LICENSE` with it.
