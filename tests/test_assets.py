"""Redistributable Darwin assets: stdlib-only KDE contract checks.

Run: python3 -m unittest discover -s tests -v
SPDX-License-Identifier: MIT
"""
import configparser
import gzip
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ID = "Darwin-Dark"
SLICES = ("center", "top", "bottom", "left", "right", "topleft", "topright", "bottomleft", "bottomright")


def ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    with path.open(encoding="utf-8") as stream:
        parser.read_file(stream)
    return parser


class AssetContracts(unittest.TestCase):
    def asset(self, *parts):
        path = ASSETS.joinpath(*parts)
        self.assertTrue(path.is_file(), f"Missing asset: {path.relative_to(ROOT)}")
        return path

    def svg(self, *parts):
        root = ET.parse(self.asset(*parts)).getroot()
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        ids = [e.get("id") for e in root.iter() if e.get("id")]
        self.assertEqual(len(ids), len(set(ids)), "SVG IDs must be unique")
        return {e.get("id"): e for e in root.iter() if e.get("id")}

    def test_aurorae_compact_geometry_and_frames(self):
        meta = json.loads(self.asset("aurorae", ID, "metadata.json").read_text())
        self.assertEqual(meta["KPlugin"]["Id"], ID)
        self.assertEqual(meta["KPlugin"]["License"], "MIT")
        cfg = ini(self.asset("aurorae", ID, ID + "rc"))
        layout = cfg["Layout"]
        self.assertEqual(int(layout["TitleHeight"]) + int(layout["TitleEdgeTop"]) + int(layout["TitleEdgeBottom"]), 32)
        for key in ("ButtonWidth", "ButtonHeight"):
            self.assertEqual(int(layout[key]), 14)
        self.assertEqual(int(layout["ButtonSpacing"]), 9)
        self.assertEqual(int(layout["TitleEdgeTop"]) + int(layout["ButtonMarginTop"]), 9)
        self.assertEqual(cfg["General"]["LeftButtons"], "XIA")
        self.assertEqual(cfg["General"]["RightButtons"], "")
        ids = self.svg("aurorae", ID, "decoration.svg")
        for prefix in ("decoration", "decoration-inactive"):
            for part in SLICES:
                self.assertIn(f"{prefix}-{part}", ids)
        # The top corners have a native 16px radius, not a bitmap approximation.
        self.assertTrue(any("16" in e.get("d", "") for e in ids["decoration-topleft"].iter()))
        self.assertEqual(ids["decoration-center"].get("fill"), "#141414")
        self.assertIn("decoration-maximized-center", ids)
        self.assertIn("decoration-maximized-inactive-center", ids)
        for name in ("close", "minimize", "maximize", "restore", "keepabove", "keepbelow", "alldesktops", "shade", "help"):
            buttons = self.svg("aurorae", ID, name + ".svg")
            for state in ("active", "hover", "pressed", "inactive", "hover-inactive", "pressed-inactive", "deactivated", "deactivated-inactive"):
                self.assertIn(state + "-center", buttons)
            circles = list(buttons["active-center"].iter("{http://www.w3.org/2000/svg}circle"))
            self.assertTrue(circles)
            self.assertEqual(float(circles[0].get("r")), 7)


    def test_plasma_panel_contract(self):
        meta = json.loads(self.asset("plasma", ID, "metadata.json").read_text())
        self.assertEqual(meta["KPlugin"]["Id"], ID)
        self.assertEqual(meta["KPlugin"]["License"], "MIT")
        self.assertEqual(meta["X-Plasma-API"], "5.0")
        cfg = ini(self.asset("plasma", ID, "plasmarc"))
        self.assertEqual(cfg["Settings"]["FallbackTheme"], "default")
        self.assertEqual(cfg["BlurBehindEffect"]["enabled"], "false")  # see plasmarc: shared input/blur mask
        for variant in ((), ("solid",), ("opaque",)):
            ids = self.svg("plasma", ID, *variant, "widgets", "panel-background.svg")
            for prefix in ("", "mask-", "floating-", "floating-mask-", "thick-", "shadow-"):
                for part in SLICES:
                    self.assertIn(prefix + part, ids)
            for prefix in ("", "floating-", "thick-"):
                for edge in ("top", "bottom", "left", "right"):
                    self.assertIn(prefix + "hint-" + edge + "-margin", ids)
            self.assertIn("hint-tile-center", ids)
            alpha = float(ids["center"].get("fill-opacity", "1"))
            # The top bar uses the translucent file; the dock panel uses the solid/opaque files and
            # must stay invisible because the dock plasmoid draws its own glass.
            self.assertEqual(alpha, 0 if variant else .84)


    def test_palette_and_global_theme_resolve_to_shipped_assets(self):
        scheme = ini(self.asset("color-schemes", "DarwinDark.colors"))
        self.assertEqual(scheme["Colors:Window"]["BackgroundNormal"], "20,20,20")
        self.assertEqual(scheme["Colors:View"]["BackgroundNormal"], "13,13,13")
        self.assertEqual(scheme["Colors:Selection"]["BackgroundNormal"], "0,145,255")
        for group in ("Window", "View", "Button", "Selection", "Tooltip", "Complementary", "Header"):
            for key in ("BackgroundNormal", "BackgroundAlternate", "ForegroundNormal", "ForegroundInactive", "DecorationFocus", "DecorationHover"):
                rgb = scheme["Colors:" + group][key].split(",")
                self.assertEqual(len(rgb), 3)
                self.assertTrue(all(0 <= int(c) <= 255 for c in rgb))
        panel_colors = self.asset("plasma", ID, "colors")
        self.assertEqual(panel_colors.read_bytes(), (ASSETS/"color-schemes"/"DarwinDark.colors").read_bytes())
        laf = "com.prashantjain25.darwin.dark"
        meta = json.loads(self.asset("look-and-feel", laf, "metadata.json").read_text())
        self.assertEqual(meta["KPlugin"]["Id"], laf)
        self.assertEqual(meta["KPlugin"]["License"], "MIT")
        defaults = ini(self.asset("look-and-feel", laf, "contents", "defaults"))
        self.assertEqual(defaults["plasmarc][Theme"]["name"], ID)
        self.assertEqual(defaults["kdeglobals][General"]["ColorScheme"], "DarwinDark")
        self.assertEqual(defaults["kwinrc][org.kde.kdecoration2"]["library"], "org.kde.kwin.aurorae")
        self.assertEqual(defaults["kwinrc][org.kde.kdecoration2"]["theme"], "__aurorae__svg__" + ID)
        self.assertEqual(defaults["kwinrc][org.kde.kdecoration2"]["ButtonsOnLeft"], "XIA")
        self.assertEqual(defaults["kwinrc][org.kde.kdecoration2"]["ButtonsOnRight"], "")
        self.assertEqual(defaults["auroraerc][" + ID]["ButtonSize"], "1")


    def test_frame_rims_do_not_expand_nine_slice_bounds(self):
        # QtSvg expands stroked path bounding boxes by half the pen width,
        # including butt endpoints. In tiled frame edges that creates seams.
        paths = [self.asset("aurorae", ID, "decoration.svg")]
        paths += sorted((ASSETS/"plasma"/ID).rglob("panel-background.svg"))
        for path in paths:
            for node in ET.parse(path).iter():
                self.assertIn(node.get("stroke", "none"), ("none", "transparent"), str(path))

    def test_aurorae_kpackage_contract(self):
        meta = json.loads(self.asset("aurorae", ID, "metadata.json").read_text())
        self.assertEqual(meta["KPackageStructure"], "KWin/Aurorae")
        compressed = self.asset("aurorae", ID, "decoration.svgz")
        self.assertEqual(gzip.decompress(compressed.read_bytes()), self.asset("aurorae", ID, "decoration.svg").read_bytes())


    def test_assets_are_self_contained_and_mit_licensed(self):
        packages = [("aurorae", ID), ("plasma", ID), ("color-schemes",), ("look-and-feel", "com.prashantjain25.darwin.dark")]
        for package in packages:
            license_text = self.asset(*package, "LICENSE.txt").read_text()
            self.assertIn("MIT License", license_text)
            self.assertIn("Permission is hereby granted", license_text)
        svgs = sorted((ASSETS/"aurorae"/ID).rglob("*.svg")) + sorted((ASSETS/"plasma"/ID).rglob("*.svg"))
        self.assertGreaterEqual(len(svgs), 14)
        for path in svgs:
            data = path.read_text()
            self.assertIn("SPDX-License-Identifier: MIT", data)
            self.assertNotIn("<!ENTITY", data)
            self.assertNotIn("<!DOCTYPE", data)
            root = ET.fromstring(data)
            ids = [e.get("id") for e in root.iter() if e.get("id")]
            self.assertEqual(len(ids), len(set(ids)), str(path))
            for node in root.iter():
                self.assertNotIn(node.tag.rsplit("}", 1)[-1], ("script", "image", "text", "foreignObject", "font", "font-face"))
                for key, value in node.attrib.items():
                    if key.rsplit("}", 1)[-1] == "href":
                        self.assertTrue(value.startswith("#"), (path, value))
                    if value.startswith("url("):
                        self.assertTrue(value.startswith("url(#"), (path, value))
                        self.assertIn(value[5:-1], ids)


if __name__ == "__main__":
    unittest.main()
