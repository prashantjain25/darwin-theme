# Darwin Dock (Plasma 6 / Wayland)

Original MIT-licensed QML, using the installed `org.kde.taskmanager.TasksModel`
for real pinned applications, running windows, grouping, launch, activation and
minimization. No stock task-manager UI is embedded. Icons use your installed icon
theme; this package does not replace application artwork.

## Integrating (installer/parent)

Package ID: `com.prashantjain25.darwin.dock`.

```sh
kpackagetool6 --type Plasma/Applet --install "$PWD/assets/plasmoids/com.prashantjain25.darwin.dock"
# If already installed, use --upgrade rather than --install.
```

**Before removing the old task widget, read its General/launchers StringList.**
Create this applet on the existing bottom panel, set its General config group,
write the *entire original array* to `launchers` and reload the config. Only then
remove the old icon task manager. Keep the old applet/config in the installer's
backup. Do not seed a curated launcher list over the user's pins. Empty defaults
are intentional. The widget also has a native Configure → Dock page for editing
one URL per line without changing URL syntax or internal spaces.

Plasma scripting sketch (integration owns the panel and original `pins`):

```js
var dock = panel.addWidget("com.prashantjain25.darwin.dock");
dock.currentConfigGroup = ["General"];
dock.writeConfig("launchers", pins); // Original StringList, not a guessed CSV
// Current 2560 logical px / scale 1: 36 × 2560 / 1512 ≈ 61.
dock.writeConfig("iconSize", 60);
dock.writeConfig("zoomFactor", 1.55);
dock.writeConfig("showTrash", true);
dock.reloadConfig();
panel.height = 112;
// Disable containment/native panel background in the owning panel layout.
```

The applet requests NoBackground, but the **containment panel** must also have
its native background disabled; otherwise two different rims will be visible.
Use a bottom horizontal panel, fit-content sizing, center alignment, and the
parent's desired auto-hide policy. Do not put spacers around this widget.

### Config (`General`)

| Key | Type | Default |
| --- | --- | --- |
| `launchers` | StringList | empty; supply original pins |
| `iconSize` | Int | 60 |
| `zoomFactor` | Double | 1.55 |
| `showDownloads` | Bool | false |
| `showTrash` | Bool | true |
| `utilityLaunchers` | StringList | applications:systemsettings.desktop |

`utilityLaunchers` only moves matching existing native tasks after the separator;
it never adds or duplicates a pin. Other pins retain relative order. A small
queued native-model reorder also corrects initial TasksModel alphabetical order
without rewriting the saved launcher URLs. Invalid/unavailable launchers remain
in configuration even if KDE cannot represent them.

Default painted glass is 76px high, while the transparent icon canvas is 110px.
The latter is fixed on purpose: resizing a Wayland panel window on every hover
clips magnification and flickers auto-hide. At 48px icons, the glass is 64px.
Minimum panel height is `ceil(iconSize * zoomFactor + 17)`; 112px is appropriate
for the current default. Hover grows 60px → 93px with animated neighbour movement,
not a rectangular button highlight. Kirigami size quantization is disabled.

Left click launches a pin, activates/restores an inactive/minimized window, or
minimizes the active window. Grouped tasks cycle native child windows. Middle
click / Shift-click requests a new instance. Enter/Space and accessibility press
also activate. The trailing trash opens `trash:/`; Downloads uses Qt's standard
user download directory. No destructive empty-trash action is provided.

## Verification without installation or live config edits

```sh
/usr/lib/qt6/bin/qmllint -I /usr/lib/x86_64-linux-gnu/qt6/qml -W 0 \
  assets/plasmoids/com.prashantjain25.darwin.dock/contents/ui/*.qml \
  assets/plasmoids/com.prashantjain25.darwin.dock/contents/config/config.qml
DARWIN_QML_TEST=1 /usr/bin/python3 -m unittest discover -s tests -p test_dock_component.py -v
/usr/bin/python3 assets/plasmoids/com.prashantjain25.darwin.dock/tools/preview.py \
  --output "$TMPDIR/darwin-dock-preview" --test --nested
```

Requires system PyQt6 QtQuick/QtTest, KDE QML modules, `kwin_wayland`,
`dbus-run-session`, `kbuildsycoca6`. `--nested` starts an isolated virtual KWin
compositor and private D-Bus session, with config/cache/application registration
under the requested output directory only. It verifies an actual mouse click
launching an isolated native .desktop marker, real window activation/minimize /
restore through TasksModel, preserved launcher values/order, pointer zoom/reset,
and collects QML engine warnings. It saves `dock-idle.png`, `dock-hover.png`,
`report.json`, and `nested-session.log`.

Plain Qt's offscreen platform does not populate this installed TasksModel;
headless **Wayland KWin** is the actual tested path. A standalone `--wayland`
preview on the user's compositor can show launchers but KWin correctly denies
Python the privileged window-management protocol. The installed applet runs
inside plasmashell, which already has that permission. Do not disable permission
checks on the live compositor. Nested tests can emit portal/PipeWire/systemd
setup warnings; these are not QML warnings. See `report.json` for the QML result.

The preview tests the exact Dock.qml surface and backend, not a live installed
panel. Final containment height/background/auto-hide and screen comparison remain
integration checks. Glass is translucent original Qt vector geometry with a
rounded rim; compositor blur is not independently requested by this applet.
