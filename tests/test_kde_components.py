import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KDEComponentHelpersTests(unittest.TestCase):
    def module(self):
        path = ROOT / 'lib/kde_components.py'
        self.assertTrue(path.exists(), 'KDE component integration is missing')
        spec = importlib.util.spec_from_file_location('components', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_gvariant_shortcuts_are_typed_integers(self):
        module = self.module()
        self.assertEqual(module.shortcut_keys('([134217760, 16777266],)'), [134217760, 16777266])
        self.assertEqual(module.shortcut_keys('(@ai [],)'), [])
        with self.assertRaises(ValueError):
            module.shortcut_keys("(['not-a-key'],)")

    def test_shortcuts_are_snapshotted_and_conflicts_are_not_stolen(self):
        import json
        import tempfile
        module = self.module()
        self.assertTrue(hasattr(module, 'register_spotlight_shortcuts'), 'Shortcut registration is missing')
        with tempfile.TemporaryDirectory() as directory:
            class Tx:
                from pathlib import Path
                paths = {'config': Path(directory)}
                def capture(self, path):
                    pass
            tx = Tx()
            tx.directory = Path(directory)
            calls = []
            def rpc(command):
                calls.append(command)
                method = command[command.index('--method') + 1].rsplit('.', 1)[-1]
                if method == 'shortcut':
                    return '(@ai [],)'
                if method == 'isGlobalShortcutAvailable':
                    return '(false,)'
                raise AssertionError('A conflicting shortcut must not be registered: ' + method)
            warnings = module.register_spotlight_shortcuts(tx, rpc)
            self.assertEqual(len(warnings), 3)
            self.assertFalse(any('setShortcut' in str(call) for call in calls))
            self.assertEqual(json.loads((tx.directory / 'runtime.json').read_text())['shortcuts'], [])
    def test_old_shortcut_sections_are_dropped_and_others_kept(self):
        module = self.module()
        text = ("[services][golden-gate-spotlight.desktop]\n_launch=Meta+Space\n\n"
                "[services][golden-gate-spotlight-files.desktop]\n_launch=Meta+Shift+Space\n\n"
                "[services][darwin-spotlight.desktop]\n_launch=Meta+Space\n\n"
                "[services][org.kde.spectacle.desktop]\nOpenWithoutScreenshot=\n")
        cleaned = module.drop_legacy_sections(text)
        self.assertNotIn('golden-gate', cleaned)
        self.assertIn('[services][darwin-spotlight.desktop]\n_launch=Meta+Space', cleaned)
        self.assertIn('[services][org.kde.spectacle.desktop]', cleaned)

    def test_desktop_exec_quotes_paths_without_shell_interpretation(self):
        module = self.module()
        quoted = module.desktop_quote('/home/test/Library $a/100%/"spotlight".py')
        self.assertEqual(quoted, '"/home/test/Library \\$a/100%%/\\"spotlight\\".py"')
        with self.assertRaises(ValueError):
            module.desktop_quote('/home/test/invalid\nExec=bad')

    def test_shortcuts_are_registered_present_so_kde_activates_them(self):
        import json
        import tempfile
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            class Tx:
                from pathlib import Path
                paths = {'config': Path(directory)}
                def capture(self, path):
                    pass
            tx = Tx()
            tx.directory = Path(directory)
            seen = []
            def rpc(command):
                method = command[command.index('--method') + 1].rsplit('.', 1)[-1]
                if method == 'shortcut':
                    return '(@ai [],)'
                if method == 'isGlobalShortcutAvailable':
                    return '(true,)'
                if method == 'setShortcut':
                    seen.append(command[-1])
                    return '(' + command[-2] + ',)'
                return '()'
            module.register_spotlight_shortcuts(tx, rpc)
            # 2 (SetPresent) | 4 (NoAutoloading): without "present" KDE stores the key but never fires it.
            self.assertEqual(seen, ['6', '6', '6'])


if __name__ == '__main__':
    unittest.main()
