# Darwin — native Plasma 6 window switcher

KWin `KWin/WindowSwitcher` package, ID **Darwin**. Install the whole directory
as `$XDG_DATA_HOME/kwin/tabbox/Darwin` (normally
`~/.local/share/kwin/tabbox/Darwin`) and select `LayoutName=Darwin` in
kwinrc's `[TabBox]` group. The installer owns settings, backups and reloads;
this package never writes configuration or registers global shortcuts.

## Native behavior

`main.qml` uses the Plasma 6.6 `KWin.TabBoxSwitcher`/`Instantiator` lifecycle,
`PlasmaCore.Dialog`, KWin's window model, bidirectional current-index updates
and the model's `activate(index)` method. KWin—not this QML—owns Alt+Tab,
Shift+Alt+Tab, modifier-release acceptance and Escape cancellation. Left/right
arrows and pointer selection update that same native selection.

There is **one tile per model row/window**, including multiple windows of the
same application. The package never substitutes a task-manager/application
model, groups rows, or changes KWin's filtering policy. The caller must retain
KWin's **All windows** application mode (`ApplicationsMode=0` in `[TabBox]`),
not “one window per application.” `ShowDesktopMode=0` excludes KWin's optional
“Peek at Desktop” row, matching the original overlay's windows-only list.

KWin's ClientModel has `windowId`, `icon` and `caption` roles but **no application
name role**. Application labels therefore resolve each window UUID against
`KWin.Workspace.windows`, using the window's `resourceClass` (with resource-name
and desktop-file-name fallbacks). Familiar class aliases match the original
LXQt switcher. Unknown classes use a shortened, initial-capitalized application
identifier, never the document/window caption. This is Wayland-safe; there are
no X11 grabs, polling, subprocesses or external helpers.

## Appearance

- Background `#dedede` at 67% opacity, radius 20; no Plasma theme frame.
- Height 148, normal horizontal padding 20, tile width 108, icon size 88.
- Selected tile at y=20, height 108, radius 7, black alpha 40/255.
- Selected application label only, y=129, height 18, 10pt, `#1a1a1a`, directly
  below the selected icon; elided as needed. No centered window-title footer.
- The popup stays within the output minus 40 logical pixels. Tiles/icons first
  shrink horizontally; once tiles reach 44 pixels, the clipped horizontal strip
  scrolls to the selected window instead of overflowing or wrapping vertically.
- No thumbnails, focus pill, accent-color selection or bundled icon artwork.
  Icons come directly from KWin's window model.

This reproduces the original overlay's translucent fill; it does not promise
compositor blur when the system's blur effect is unavailable or disabled.

## Validation

From the repository root:

```sh
python3 -m unittest discover -s tests -p test_switcher_component.py -v
kpackagetool6 --type KWin/WindowSwitcher --show "$PWD/assets/tabbox/Darwin"
/usr/lib/qt6/bin/qmllint assets/tabbox/Darwin/contents/ui/DarwinView.qml
```

The test suite includes stdlib-only contracts and, when system PyQt6 QtQuick is
available, an actual offscreen render of the production `DarwinView.qml`
using installed Qt/Kirigami. The fixture preserves duplicate application
windows and uses stock KDE/hicolor SVGs, not the user's current icon theme.
To save wide/narrow preview PNGs:

```sh
DARWIN_SWITCHER_PREVIEW_DIR="$TMPDIR/darwin-switcher" \
  python3 -m unittest discover -s tests -p test_switcher_component.py -v
```

`org.kde.kwin`/`TabBoxSwitcher` is registered **inside KWin**, not as a standalone
QML plugin. Consequently standalone qmllint/qml of `main.qml` cannot resolve
that import. The visual component can be linted and rendered independently;
full keyboard-grab/release/cancel behavior must be verified inside KWin. An
outside-KWin test shim is not a substitute for that live integration test.

## License and attribution

GPL-2.0-or-later; see `LICENSE.txt` for GPL v2 and the SPDX license notices in
QML. Native wrapper lifecycle derived from KDE's `big_icons/contents/ui/main.qml`
by Martin Gräßlin, copyright 2011. The Darwin view is authored for this
package. No Apple artwork or third-party icon files are included.
