"""Darwin Spotlight behavioral tests (stdlib; optional PyQt6 GUI checks)."""
import importlib.util
from pathlib import Path
import sys
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / "assets" / "spotlight"
sys.path.insert(0, str(PACKAGE))


class CalculatorTests(unittest.TestCase):
    def test_safe_arithmetic_and_resource_limits(self):
        self.assertIsNotNone(importlib.util.find_spec("core"), "Spotlight core is not implemented")
        from core import calculate
        for text, expected in (("2 + 3 * 4", "14"), ("(12 - 2) / 4", "2.5"),
                               ("-2**3", "-8"), ("7 % 4", "3"), ("= 2^3", "8")):
            with self.subTest(text=text):
                self.assertEqual(calculate(text), expected)
        for text in ("__import__('os').system('id')", "open('/etc/passwd')", "x + 2",
                     "True + 1", "[1,2]", "1/0", "2**100000000", "9**9**9",
                     "1e999", "2*" , "2" * 600, "(1+2j)"):
            with self.subTest(text=text):
                self.assertIsNone(calculate(text))


class CurrencyAndConversionTests(unittest.TestCase):
    RATES = {"EUR": 1.0, "USD": 1.08, "INR": 90.0}

    def test_currency_conversion_uses_reference_rates(self):
        from core import convert_currency
        self.assertEqual(convert_currency("100 usd to eur", self.RATES), "92.59 EUR")
        self.assertEqual(convert_currency("1,000 EUR in INR", self.RATES), "90,000.00 INR")
        self.assertEqual(convert_currency("usd -> inr", self.RATES), "83.33 INR")   # amount defaults to 1
        for text in ("100 usd to xyz", "100 usd", "ten usd to eur", "100 usd to eur; rm -rf /"):
            with self.subTest(text=text):
                self.assertIsNone(convert_currency(text, self.RATES))

    def test_expression_detection(self):
        from core import looks_like_math, looks_like_conversion
        self.assertTrue(looks_like_math("2+3*4"))
        self.assertFalse(looks_like_math("2024"))        # a bare number is a file/app query, not a calculation
        self.assertTrue(looks_like_conversion("100 usd to eur"))
        self.assertFalse(looks_like_conversion("firefox"))

    def test_rates_are_cached_and_offline_falls_back_to_stale_rates(self):
        import json
        import tempfile
        from core import ecb_rates
        xml = "<Cube currency='USD' rate='1.1000'/><Cube currency='INR' rate='95.5'/>"
        calls = []
        def fetch():
            calls.append(1)
            return xml
        with tempfile.TemporaryDirectory() as directory:
            rates = ecb_rates(directory, now=1000, fetch=fetch)
            self.assertEqual((rates["EUR"], rates["USD"], rates["INR"]), (1.0, 1.1, 95.5))
            ecb_rates(directory, now=2000, fetch=fetch)       # fresh cache: no second download
            self.assertEqual(len(calls), 1)
            def offline():
                raise OSError("no network")
            stale = ecb_rates(directory, now=1000 + 13 * 3600, fetch=offline)
            self.assertEqual(stale["USD"], 1.1)               # stale beats nothing when offline
        with tempfile.TemporaryDirectory() as empty:
            self.assertIsNone(ecb_rates(empty, now=1, fetch=offline))

    def test_unified_evaluator_prefers_instant_arithmetic(self):
        from core import evaluate_expression
        self.assertEqual(evaluate_expression("2+3*4"), "14")


class ApplicationCacheTests(unittest.TestCase):
    def test_cache_is_reused_and_refreshes_when_a_desktop_file_changes(self):
        import tempfile
        import core
        with tempfile.TemporaryDirectory() as tmp:
            apps_dir, cache = Path(tmp) / "applications", Path(tmp) / "cache"
            apps_dir.mkdir()
            def write(name, title):
                (apps_dir / name).write_text(f"[Desktop Entry]\nType=Application\nName={title}\nExec=true\n")
            write("one.desktop", "One")
            scans = []
            real = core.load_applications
            core.load_applications = lambda *a, **k: scans.append(1) or real(*a, **k)
            try:
                first = core.load_applications_cached(cache, [apps_dir], "KDE")
                second = core.load_applications_cached(cache, [apps_dir], "KDE")
                self.assertEqual([a.name for a in first], ["One"])
                self.assertEqual(first, second)
                self.assertEqual(len(scans), 1, "unchanged files must not be rescanned")
                write("two.desktop", "Two")           # a new application appears
                third = core.load_applications_cached(cache, [apps_dir], "KDE")
                self.assertEqual([a.name for a in third], ["One", "Two"])
                import os, time
                path = apps_dir / "one.desktop"
                path.write_text("[Desktop Entry]\nType=Application\nName=Uno\nExec=true\n")
                os.utime(path, (time.time() + 5, time.time() + 5))   # an edit changes the modification time
                fourth = core.load_applications_cached(cache, [apps_dir], "KDE")
                self.assertEqual(sorted(a.name for a in fourth), ["Two", "Uno"])
                (cache / "apps.json").write_text("not json")        # a damaged cache falls back to a full scan
                self.assertEqual(len(core.load_applications_cached(cache, [apps_dir], "KDE")), 2)
            finally:
                core.load_applications = real


class ApplicationTests(unittest.TestCase):
    def test_xdg_overrides_visibility_and_ranked_real_desktop_search(self):
        import tempfile
        import core
        self.assertTrue(hasattr(core, "load_applications"), "desktop discovery missing")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user, system = root / "user", root / "system"
            user.mkdir()
            system.mkdir()
            def desktop(where, filename, values):
                (where / filename).write_text("[Desktop Entry]\nType=Application\nExec=/usr/bin/true %U\n" + values)
            desktop(system, "editor.desktop", "Name=Text Editor\nGenericName=Writing\nKeywords=note;document;\n")
            desktop(system, "files.desktop", "Name=Files\nOnlyShowIn=KDE;\nIcon=system-file-manager\n")
            desktop(system, "masked.desktop", "Name=Masked\n")
            desktop(user, "masked.desktop", "Hidden=true\n")
            desktop(system, "hidden.desktop", "Name=Hidden\nNoDisplay=true\n")
            desktop(system, "gnome.desktop", "Name=GNOME Only\nOnlyShowIn=GNOME;\n")
            desktop(system, "missing.desktop", "Name=Missing\nTryExec=darwin-no-such-executable\n")
            apps = core.load_applications([user, system], current_desktop="KDE")
            self.assertEqual({a.name for a in apps}, {"Text Editor", "Files"})
            self.assertEqual(core.search_applications(apps, "note")[0].name, "Text Editor")
            self.assertEqual(core.search_applications(apps, "files")[0].desktop_file, str(system / "files.desktop"))
            self.assertEqual(core.search_applications(apps, "no match whatsoever"), [])
            self.assertEqual(len(core.search_applications(apps, "", limit=1)), 1)
        installed = core.load_applications()
        self.assertGreater(len(installed), 0, "test host must have real desktop applications")
        app = installed[0]
        self.assertIn(app, core.search_applications(installed, app.name, limit=100))


class FileSearchTests(unittest.TestCase):
    def test_bounded_real_file_search_and_cancellation(self):
        import tempfile
        import threading
        import time
        import core
        self.assertTrue(hasattr(core, "find_files"), "bounded file search missing")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested").mkdir()
            for i in range(12):
                (root / "nested" / f"darwin-{i}.txt").write_text("not read by search")
            (root / "other.txt").touch()
            matches = core.find_files("darwin", roots=[root], limit=7, use_indexes=False)
            self.assertEqual(len(matches), 7)
            self.assertTrue(all(p.is_file() and "darwin" in p.name for p in matches))
            indexed_start = time.monotonic()
            indexed = core.find_files("darwin", roots=[root], limit=7, use_indexes=True)
            self.assertEqual(len(indexed), 7, "index miss must fall back to bounded real files")
            self.assertLess(time.monotonic() - indexed_start, 1.5)
            self.assertEqual(core.find_files("", roots=[root]), [])
            self.assertEqual(core.find_files("; touch unsafe", roots=[root], use_indexes=False), [])
            cancel = threading.Event()
            cancel.set()
            start = time.monotonic()
            self.assertEqual(core.find_files("darwin", roots=[root], cancelled=cancel), [])
            self.assertLess(time.monotonic() - start, 0.2)


class LaunchTests(unittest.TestCase):
    def test_gio_preserves_desktop_exec_fields_without_shell(self):
        self.assertIsNotNone(importlib.util.find_spec("desktop_launch"), "Gio launch adapter missing")
        if importlib.util.find_spec("gi") is None:
            self.skipTest("system Python with python3-gi required for Gio integration")
        import desktop_launch
        import json
        import tempfile
        import time
        with tempfile.TemporaryDirectory(prefix="spotlight exec ") as tmp:
            root = Path(tmp)
            script = root / "record.py"
            output = root / "args.json"
            script.write_text("import json,sys,pathlib\npathlib.Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))\n")
            entry = root / "exec semantics.desktop"
            entry.write_text('[Desktop Entry]\nType=Application\nName=Spotlight Test\n'
                             f'Exec=/usr/bin/python3 "{script}" "{output}" "a b" "semi;literal" %c %k %U\n')
            desktop_launch.launch_application(str(entry))
            deadline = time.monotonic() + 3
            while not output.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(output.exists(), "real Gio launch did not execute desktop file")
            self.assertEqual(json.loads(output.read_text()), ["a b", "semi;literal", "Spotlight Test", str(entry)])
            with self.assertRaises((RuntimeError, ValueError)):
                desktop_launch.launch_application(str(root / "does-not-exist.desktop"))


@unittest.skipUnless(importlib.util.find_spec("PyQt6"), "system PyQt6 required")
class GuiTests(unittest.TestCase):
    def test_real_widget_render_keyboard_focus_guard_and_socket_toggle(self):
        self.assertIsNotNone(importlib.util.find_spec("spotlight"), "Qt Spotlight widget missing")
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import tempfile
        import time
        from PyQt6.QtCore import QRect, Qt, QEvent, qInstallMessageHandler, QtMsgType
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QApplication
        import spotlight
        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        failures = []
        previous = qInstallMessageHandler(lambda kind, context, text: failures.append(text)
                    if kind in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg) else None)
        window = spotlight.Spotlight(screen_geometry=QRect(0, 0, 2560, 1440))
        try:
            window.show_launcher("apps")
            # Initial compositor focus churn, before the startup grace expires.
            app.sendEvent(window, QEvent(QEvent.Type.WindowDeactivate))
            self.assertTrue(window.isVisible())
            deadline = time.monotonic() + 5
            while not window.results.count() and time.monotonic() < deadline:
                app.processEvents()
                QTest.qWait(20)
            self.assertEqual(window.width(), 640)
            self.assertEqual(window.input.placeholderText(), "Spotlight Search")
            self.assertGreater(window.results.count(), 1)
            self.assertLessEqual(window.results.count(), 7)
            self.assertFalse(window.results.item(0).icon().isNull(), "real app icons must resolve without KDE Qt platform plugin")
            self.assertTrue(all(Path(window.results.item(i).data(Qt.ItemDataRole.UserRole).target).is_file()
                                for i in range(window.results.count())))
            QTest.keyClick(window.input, Qt.Key.Key_Down)
            self.assertEqual(window.results.currentRow(), 1)
            QTest.keyClick(window.input, Qt.Key.Key_Up)
            self.assertEqual(window.results.currentRow(), 0)
            screenshot = Path(os.environ.get("SPOTLIGHT_SCREENSHOT", tempfile.gettempdir() + "/darwin-spotlight.png"))
            self.assertTrue(window.grab().save(str(screenshot)))
            self.assertGreater(screenshot.stat().st_size, 1000)
            print("Spotlight real-app screenshot:", screenshot)
            window.input.setText("darwin-no-such-app-79df")
            self.assertEqual(window.results.count(), 0, "typed query must invalidate the old selection before Enter")
            QTest.keyClick(window.input, Qt.Key.Key_Escape)
            self.assertFalse(window.isVisible())
            window.show_launcher("calc")
            window.input.setText("(12 + 3) * 2")
            QTest.qWait(180)
            self.assertEqual(window.results.count(), 1)
            QTest.keyClick(window.input, Qt.Key.Key_Return)
            self.assertEqual(app.clipboard().text(), "30")
            self.assertFalse(window.isVisible())
            window.show_launcher("files")
            file_start = time.monotonic()
            window.input.setText("darwin-no-such-file-79df")
            self.assertLess(time.monotonic() - file_start, .1, "file search must not block input")
            QTest.qWait(450)
            app.sendEvent(window, QEvent(QEvent.Type.WindowActivate))
            app.sendEvent(window, QEvent(QEvent.Type.WindowDeactivate))
            self.assertFalse(window.isVisible(), "genuine post-activation focus loss dismisses")
            with tempfile.TemporaryDirectory() as tmp:
                broker = spotlight.InstanceBroker(str(Path(tmp) / "instance.sock"))
                received = []
                broker.message.connect(received.append)
                self.assertTrue(broker.claim("apps"))
                second = spotlight.InstanceBroker(str(Path(tmp) / "instance.sock"))
                self.assertFalse(second.claim("files"))
                deadline = time.monotonic() + 2
                while not received and time.monotonic() < deadline:
                    app.processEvents()
                    QTest.qWait(10)
                self.assertEqual(received[0]["mode"], "files")
                broker.close()
            self.assertEqual(failures, [], "Qt critical/fatal runtime messages")
        finally:
            window.shutdown()
            qInstallMessageHandler(previous)


    def test_cli_second_launch_exits_first_and_next_launch_is_fresh(self):
        import os
        import subprocess
        import tempfile
        import time
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            runtime.chmod(0o700)
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_RUNTIME_DIR=str(runtime))
            command = ["/usr/bin/python3", str(PACKAGE / "spotlight.py")]
            def cycle(mode, dismiss_args):
                first = subprocess.Popen(command + ["--mode", mode], env=env,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    deadline = time.monotonic() + 4
                    while not (runtime / "darwin-spotlight.sock").exists() and first.poll() is None and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertTrue((runtime / "darwin-spotlight.sock").exists(), "primary did not start its socket")
                    second = subprocess.run(command + dismiss_args, env=env, capture_output=True, text=True, timeout=5)
                    self.assertEqual(second.returncode, 0, second.stderr)
                    out, err = first.communicate(timeout=5)
                    self.assertEqual(first.returncode, 0, err)
                    for bad in ("Traceback", "QThread: Destroyed", "Segmentation fault"):
                        self.assertNotIn(bad, err)
                    self.assertFalse((runtime / "darwin-spotlight.sock").exists(), "closed primary left a server behind")
                finally:
                    if first.poll() is None:
                        first.kill()
                        first.communicate()
            cycle("apps", ["--mode", "apps"])
            cycle("calc", ["--quit"])


class DesktopTemplateTests(unittest.TestCase):
    def test_desktop_has_predictable_id_fresh_activation_and_three_modes(self):
        import configparser
        template = PACKAGE / "darwin-spotlight.desktop.in"
        self.assertTrue(template.is_file(), "desktop activation template missing")
        config = configparser.ConfigParser(interpolation=None)
        config.read(template)
        self.assertEqual(config["Desktop Entry"]["Type"], "Application")
        self.assertEqual(config["Desktop Entry"]["Exec"], "/usr/bin/python3 @SPOTLIGHT_SCRIPT@ --mode apps")
        self.assertFalse(config["Desktop Entry"].getboolean("DBusActivatable"))
        self.assertTrue(config["Desktop Entry"].getboolean("StartupNotify"))
        for mode in ("files", "calc"):
            self.assertEqual(config[f"Desktop Action {mode}"]["Exec"], f"/usr/bin/python3 @SPOTLIGHT_SCRIPT@ --mode {mode}")


if __name__ == "__main__":
    unittest.main()
