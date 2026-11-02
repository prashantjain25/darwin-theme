"""Darwin native Plasma dock contracts. SPDX-License-Identifier: MIT

Run stdlib contracts: python3 -m unittest discover -s tests -p test_dock_component.py -v
Opt-in actual Qt/task model test: DARWIN_QML_TEST=1 /usr/bin/python3 -m unittest discover -s tests -p test_dock_component.py -v
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "assets/plasmoids/com.prashantjain25.darwin.dock"


class DockComponentTests(unittest.TestCase):
    def test_plasma6_package_has_non_destructive_launcher_configuration(self):
        self.assertTrue((PACKAGE / "metadata.json").is_file(), "Native dock package must exist")
        meta = json.loads((PACKAGE / "metadata.json").read_text())
        self.assertEqual(meta["KPackageStructure"], "Plasma/Applet")
        self.assertEqual(meta["KPlugin"]["Id"], PACKAGE.name)
        self.assertEqual(meta["KPlugin"]["License"], "MIT")
        self.assertEqual(meta["X-Plasma-API-Minimum-Version"], "6.0")
        cfg = ET.parse(PACKAGE / "contents/config/main.xml")
        entries = {entry.get("name"): entry for entry in cfg.iter() if entry.tag.rsplit("}", 1)[-1] == "entry"}
        text = lambda entry: next((node.text for node in entry if node.tag.rsplit("}", 1)[-1] == "default"), None)
        self.assertEqual(entries["launchers"].get("type"), "StringList")
        self.assertFalse(text(entries["launchers"]), "Installer must supply existing pins, not replace them with curated defaults")
        self.assertEqual(text(entries["iconSize"]), "60")
        self.assertTrue((PACKAGE / "contents/config/config.qml").is_file(), "Native configuration page must expose preserved launchers")
        self.assertTrue((PACKAGE / "contents/ui/configGeneral.qml").is_file())


    def test_native_task_model_and_unpill_magnification_contract(self):
        dock = PACKAGE / "contents/ui/Dock.qml"
        self.assertTrue(dock.is_file(), "A custom native task surface, not stock icontasks, is required")
        source = dock.read_text()
        self.assertIn("TaskManager.TasksModel", source)
        self.assertIn("launcherList: root.launchers", source)
        for method in ("requestActivate", "requestToggleMinimized", "requestNewInstance", "makeModelIndex"):
            self.assertIn(method, source)
        self.assertIn("IsActive", source)
        self.assertIn("IsMinimized", source)
        self.assertIn("IsLauncher", source)
        self.assertIn("IsGroupParent", source)
        self.assertNotIn("org.kde.plasma.icontasks", source)
        self.assertNotIn("xdotool", source)
        button = (PACKAGE / "contents/ui/DockIcon.qml").read_text()
        self.assertIn("Behavior on", button)
        self.assertIn("Math.cos", button)
        self.assertNotIn("FrameSvgItem", button)
        self.assertIn("roundToIconSize: false", button, "Kirigami must not snap 60px to 48px or step hover magnification")
        self.assertIn("runningDot", button)
        self.assertTrue((PACKAGE / "contents/ui/main.qml").is_file())

    @unittest.skipUnless(os.environ.get("DARWIN_QML_TEST") == "1", "Set DARWIN_QML_TEST=1 with system Qt6/PyQt6/KDE installed")
    def test_real_qt_task_model_render_zoom_and_native_launch(self):
        with tempfile.TemporaryDirectory(prefix="darwin-dock-", dir=os.environ.get("TMPDIR")) as output:
            result = subprocess.run(["/usr/bin/python3", str(PACKAGE / "tools/preview.py"), "--output", output, "--test", "--nested"], text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(output) / "report.json").read_text())
            self.assertEqual(report["qml_errors"], [])
            self.assertTrue(report["launchers_preserved"])
            self.assertTrue(report["native_launch_verified"])
            self.assertTrue(report["native_window_requests_verified"])
            self.assertTrue(report["pin_order_preserved"])
            self.assertGreater(report["hover_icon_size"], report["idle_icon_size"])
            self.assertEqual(report["restored_icon_size"], report["idle_icon_size"])
            self.assertGreater(report["task_count"], 0)
            self.assertTrue((Path(output) / "dock-idle.png").is_file())
            self.assertTrue((Path(output) / "dock-hover.png").is_file())


if __name__ == "__main__":
    unittest.main()
