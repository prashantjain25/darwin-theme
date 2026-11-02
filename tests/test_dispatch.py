import importlib.util
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DispatchTests(unittest.TestCase):
    def test_desktop_detection_and_explicit_override(self):
        path = ROOT / 'lib/desktop.py'
        self.assertTrue(path.exists(), 'Desktop auto-detection module is missing')
        spec = importlib.util.spec_from_file_location('desktop', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for desktop in ['KDE', 'kde:plasma', 'ubuntu:KDE']:
            self.assertEqual(module.detect({'XDG_CURRENT_DESKTOP': desktop}), 'kde')
        for desktop in ['LXQt', 'lxqt:Lubuntu']:
            self.assertEqual(module.detect({'XDG_CURRENT_DESKTOP': desktop}), 'lxqt')
        self.assertEqual(module.detect({'DESKTOP_SESSION': 'plasmawayland'}), 'kde')
        self.assertEqual(module.detect({'DESKTOP_SESSION': 'Lubuntu'}), 'lxqt')
        with self.assertRaises(ValueError):
            module.detect({'XDG_CURRENT_DESKTOP': 'GNOME'})
        with self.assertRaises(ValueError):
            module.detect({'XDG_CURRENT_DESKTOP': 'KDE:LXQt'})
        self.assertEqual(module.detect({'XDG_CURRENT_DESKTOP': 'GNOME'}, 'lxqt'), 'lxqt')

    def test_lxqt_scripts_are_byte_for_byte_preserved(self):
        for name in ['install', 'dock', 'restore']:
            original = subprocess.check_output(['git', 'show', '82ef24d:' + name + '.sh'], cwd=ROOT)
            self.assertEqual((ROOT / (name + '-lxqt.sh')).read_bytes(), original)

    def test_public_entrypoint_dispatches_kde_dry_run(self):
        env = {**os.environ, 'XDG_CURRENT_DESKTOP': 'KDE'}
        result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--dry-run', '--no-restart'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Darwin-Dark', result.stdout)
        self.assertNotIn('picom', result.stdout)

    def test_lxqt_help_routes_without_running_kde(self):
        for script in ['install.sh', 'dock.sh', 'restore.sh']:
            result = subprocess.run(['bash', str(ROOT / script), '--desktop', 'lxqt', '--help'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('Darwin-Dark', result.stdout)

class PicomVersionTests(unittest.TestCase):
    def check(self, version_line):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'picom'
            fake.write_text('#!/bin/sh\necho "%s"\n' % version_line)
            fake.chmod(0o755)
            script = f'source "{ROOT}/lib/common.sh"; MISSING_NOTES=(); check_picom_version; printf "%s\\n" "${{MISSING_NOTES[@]}}"'
            env = {**os.environ, 'PATH': directory + os.pathsep + os.environ['PATH']}
            return subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True).stdout

    def test_old_picom_is_reported_and_new_picom_is_accepted(self):
        self.assertIn('too old', self.check('v10.2'))
        self.assertIn('too old', self.check('vgit-8.2-abc'))
        self.assertNotIn('too old', self.check('v12.5'))
        self.assertNotIn('too old', self.check('vgit-v13-1234abc'))


if __name__ == '__main__':
    unittest.main()
