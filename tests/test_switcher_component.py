"""Darwin native Plasma 6 task-switcher contracts (stdlib only)."""
import json
from pathlib import Path
import re
import os
import shutil
import subprocess
import unittest


# Render the production visual component with real Qt/Kirigami, not rewritten QML.
# Only the model data is a fixture; KWin owns its in-process TabBoxSwitcher type.
QT_PROBE = r'''
import json, os, sys
from pathlib import Path
from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, QUrl
from PyQt6.QtGui import QGuiApplication, QIcon
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtQuick import QQuickView, QQuickItem

app = QGuiApplication([])
class Windows(QAbstractListModel):
    def rowCount(self, parent=QModelIndex()): return 5
    def roleNames(self): return {257: b"caption", 258: b"icon", 259: b"windowId"}
    def data(self, index, role):
        if not index.isValid(): return None
        if role == 257: return "PRIVATE WINDOW TITLE " + str(index.row())
        if role == 258:
            # Absolute stock hicolor artwork avoids the user's current icon theme
            # (which may contain non-redistributable artwork) in preview images.
            name = ["org.kde.dolphin", "kwrite", "mpv", "org.kde.dolphin", "kate"][index.row()]
            icon = QIcon("/usr/share/icons/hicolor/scalable/apps/" + name + ".svg")
            assert not icon.isNull(), name
            return icon
        if role == 259: return "window-" + str(index.row())
model = Windows()
view = QQuickView()
view.setColor(Qt.GlobalColor.transparent)
view.setSource(QUrl.fromLocalFile(sys.argv[1]))
assert view.status() == QQuickView.Status.Ready, [e.toString() for e in view.errors()]
root = view.rootObject()
assert root is not None
root.setProperty("model", model)
root.setProperty("applicationLabels", {"window-0":"Dolphin", "window-1":"KWrite", "window-2":"mpv", "window-3":"Dolphin", "window-4":"Kate"})
root.setProperty("screenWidth", 1920)
root.setProperty("currentIndex", 1)
view.show()
def settle():
    for _ in range(25): app.processEvents()
settle()
def child(name):
    result = root.findChild(QQuickItem, name)
    assert result is not None, name
    return result
icons = child("windowList")
label = child("selectedApplicationLabel")
assert icons.property("count") == 5, "Duplicate app windows must stay separate"
assert root.width() == 580 and root.height() == 148, (root.width(), root.height())
assert root.property("tileWidth") == 108
assert root.property("iconSize") == 88
assert label.property("text") == "KWrite", label.property("text")
assert label.y() == 129
assert label.x() + label.width()/2 == 182, "Label must follow the selected icon, not dialog center"
assert child("glassBackground").property("radius") == 20
assert abs(child("glassBackground").property("color").alphaF() - .67) < .005
image = view.grabWindow()
icon_pixels = {image.pixelColor(x, y).rgba() for x in range(30, 118) for y in range(30, 118)}
assert len(icon_pixels) > 10, "Preview must contain a rendered native application icon, not an empty tile"
preview = os.environ.get("DARWIN_SWITCHER_PREVIEW_DIR")
if preview:
    Path(preview).mkdir(parents=True, exist_ok=True)
    assert view.grabWindow().save(str(Path(preview) / "switcher-wide.png"))
# Forward/reverse selection from KWin is mirrored without changing model rows.
for index in (2, 1, 0, 4, 3):
    root.setProperty("currentIndex", index)
    settle()
    assert icons.property("currentIndex") == index
assert label.property("text") == "Dolphin"
# Many windows / narrow output: reduce horizontal metrics, then scroll rather
# than make the popup exceed its output. Height and vertical positioning stay fixed.
results = []
for width in (600, 320, 160, 80):
    root.setProperty("screenWidth", width)
    root.setProperty("currentIndex", 4)
    settle()
    assert root.width() <= width
    assert root.height() == 148
    assert root.property("tileWidth") <= 108
    assert 0 <= label.x() <= root.width() - label.width()
    assert icons.property("contentX") >= 0
    selected = icons.property("currentItem")
    assert selected is not None
    assert selected.x() - icons.property("contentX") >= -.01
    assert selected.x() + selected.width() - icons.property("contentX") <= icons.width() + .01 or icons.width() < selected.width()
    results.append({"screen":width,"popup":root.width(),"tile":root.property("tileWidth"),"icon":root.property("iconSize")})
    if preview and width == 320:
        assert view.grabWindow().save(str(Path(preview) / "switcher-narrow.png"))
print(json.dumps({"normal_width":580,"height":148,"rows":icons.property("count"),"narrow":results}))
view.hide()
'''

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "assets/tabbox/Darwin"


class SwitcherPackageContracts(unittest.TestCase):
    def asset(self, relative):
        path = PACKAGE / relative
        self.assertTrue(path.is_file(), f"Missing task-switcher asset: {relative}")
        return path.read_text(encoding="utf-8")

    def test_native_kwin_package_and_selection_lifecycle(self):
        metadata = json.loads(self.asset("metadata.json"))
        self.assertEqual(metadata["KPackageStructure"], "KWin/WindowSwitcher")
        self.assertEqual(metadata["KPlugin"]["Id"], "Darwin")
        self.assertEqual(metadata["KPlugin"]["License"], "GPL-2.0-or-later")
        qml = self.asset("contents/ui/main.qml")
        self.assertIn("import org.kde.kwin as KWin", qml)
        self.assertIn("KWin.TabBoxSwitcher {", qml)
        self.assertIn("model: tabBox.model", qml)
        self.assertIn("tabBox.currentIndex", qml)
        self.assertIn("tabBox.model.activate(index)", qml)
        self.assertIn("active: tabBox.visible", qml)
        # KWin owns forward/reverse Tab, Alt-release acceptance and Escape cancel.
        code = re.sub(r"//[^\n]*|/\*.*?\*/", "", qml, flags=re.S)
        for forbidden in ("Qt.Key_Tab", "Qt.Key_Backtab", "Qt.Key_Alt", "Qt.Key_Escape", "Keys.onReleased", "Shortcut {", "XGrab", "WindowThumbnail", "TasksModel"):
            self.assertNotIn(forbidden, code)
        self.assertIn("SPDX-FileCopyrightText: 2011 Martin Gräßlin", qml)
        self.assertIn("SPDX-License-Identifier: GPL-2.0-or-later", qml)


    def test_original_overlay_visual_contract(self):
        qml = self.asset("contents/ui/DarwinView.qml")
        for forbidden in ("model.caption", "WindowThumbnail", "FrameSvgItem", "PlasmaComponents", "SystemPalette"):
            self.assertNotIn(forbidden, qml)
        self.assertIn('root.dark ? "#f5f5f5" : "#1a1a1a"', qml)
        self.assertIn('root.dark ? "#33ffffff" : "#28000000"', qml)
        self.assertIn("Qt.rgba(222 / 255, 222 / 255, 222 / 255, 0.67)", qml)
        self.assertIn("model.icon", qml)
        self.assertIn("model.windowId", qml)
        main = self.asset("contents/ui/main.qml")
        self.assertIn("DarwinView {", main)
        self.assertIn("PlasmaCore.Types.NoBackground", main)
        self.assertIn("KWin.Workspace.windows", main)
        self.assertIn("resourceClass", main)
        self.assertNotIn("model.caption", main)

    def test_offscreen_qt_geometry_selection_and_duplicate_windows(self):
        source = PACKAGE / "contents/ui/DarwinView.qml"
        self.assertTrue(source.is_file(), "Missing actual visual component")
        candidates = ["/usr/bin/python3", shutil.which("python3")]
        python = next((p for p in candidates if p and subprocess.run(
            [p, "-c", "import PyQt6.QtQuick"], capture_output=True).returncode == 0), None)
        if not python:
            self.skipTest("Offscreen runtime check requires PyQt6.QtQuick (contracts still run)")
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        result = subprocess.run([python, "-c", QT_PROBE, str(source)], env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for error in ("ReferenceError", "TypeError", "Binding loop", "is not installed", "is not a type", "Unable to assign"):
            self.assertNotIn(error, result.stderr)
        self.assertEqual(json.loads(result.stdout.strip())["rows"], 5)
        if os.environ.get("DARWIN_SWITCHER_PREVIEW_DIR"):
            print("\nQt runtime:", result.stdout.strip())
            print("Qt diagnostics:", result.stderr.strip() or "none")


if __name__ == "__main__":
    unittest.main()
