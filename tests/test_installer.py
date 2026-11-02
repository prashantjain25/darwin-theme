import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = {**os.environ, 'HOME': str(self.home),
                    'XDG_CONFIG_HOME': str(self.home / 'config'),
                    'XDG_DATA_HOME': str(self.home / 'data'),
                    'XDG_STATE_HOME': str(self.home / 'state')}

    @staticmethod
    def pyqt6_available():
        return subprocess.run(['/usr/bin/python3', '-c', 'import PyQt6.QtWidgets, PyQt6.QtNetwork'], capture_output=True).returncode == 0

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'lib/kde.py'), *args],
                              env=self.env, capture_output=True, text=True)

    def test_install_and_restore_preserve_original_and_remove_new_files(self):
        config = self.home / 'config'
        config.mkdir()
        original = b'# keep my unrelated preferences\n[General]\nBrowserApplication=my-browser.desktop\nfont=My Font,10\n'
        (config / 'kdeglobals').write_bytes(original)
        result = self.run_cli('install', '--no-reload', '--skip-panels')
        self.assertEqual(result.returncode, 0, result.stderr)
        changed = (config / 'kdeglobals').read_text()
        self.assertIn('BrowserApplication=my-browser.desktop', changed)
        self.assertIn('ColorScheme=DarwinDark', changed)
        for key in ['font', 'menuFont', 'toolBarFont', 'smallestReadableFont', 'activeFont']:
            value = next(line.split('=', 1)[1] for line in changed.splitlines() if line.startswith(key + '='))
            self.assertGreaterEqual(len(value.split(',')), 10, f'Qt rejects truncated QFont description: {value}')
        self.assertTrue((self.home / 'data/aurorae/themes/Darwin-Dark').is_dir())
        self.assertTrue((self.home / 'data/kwin/tabbox/Darwin/metadata.json').is_file())
        self.assertTrue((self.home / 'data/plasma/plasmoids/com.prashantjain25.darwin.dock/metadata.json').is_file())
        self.assertIn('LayoutName=Darwin', (config / 'kwinrc').read_text())
        if self.pyqt6_available():
            self.assertTrue((self.home / 'data/darwin-theme/spotlight/spotlight.py').is_file())
            self.assertIn('--mode apps', (self.home / 'data/applications/darwin-spotlight.desktop').read_text())
        else:   # without PyQt6 the launcher is skipped on purpose and KRunner stays
            self.assertFalse((self.home / 'data/applications/darwin-spotlight.desktop').exists())
        result = self.run_cli('restore', '--no-reload')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((config / 'kdeglobals').read_bytes(), original)
        self.assertFalse((config / 'kwinrc').exists())
        self.assertFalse((self.home / 'data/aurorae/themes/Darwin-Dark').exists())
        self.assertNotIn('dolphinnuc', (config / 'kdeglobals').read_text())

    def test_whitesur_icons_gtk_dark_switcher_and_fonts_are_enabled(self):
        (self.home / 'data/icons/WhiteSur-dark').mkdir(parents=True)
        (self.home / 'data/icons/WhiteSur-dark/index.theme').write_text('[Icon Theme]\nName=WhiteSur-dark\n')
        (self.home / '.themes/WhiteSur-Dark/gtk-3.0').mkdir(parents=True)
        result = self.run_cli('install', '--no-reload', '--skip-panels')
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.home / 'config'
        self.assertIn('Theme=Darwin-Icons', (config / 'kdeglobals').read_text())  # WhiteSur + tray chevrons
        self.assertIn('Inherits=WhiteSur-dark', (self.home / 'data/icons/Darwin-Icons/index.theme').read_text())
        for version in ('3', '4'):
            settings = (config / f'gtk-{version}.0/settings.ini').read_text()
            self.assertIn('gtk-theme-name=WhiteSur-Dark', settings)
            self.assertIn('gtk-icon-theme-name=WhiteSur-dark', settings)
        view = (self.home / 'data/kwin/tabbox/DarwinDark/contents/ui/DarwinView.qml').read_text()
        self.assertIn('property bool dark: true', view)  # switcher follows mode=dark
        self.assertIn('LayoutName=DarwinDark', (config / 'kwinrc').read_text())
        self.assertIn('"Id": "DarwinDark"', (self.home / 'data/kwin/tabbox/DarwinDark/metadata.json').read_text())
        self.assertIn('Maple Mono NF', (config / 'fontconfig/fonts.conf').read_text())
        self.assertIn('Inter,', (config / 'kdeglobals').read_text())
        self.assertEqual(result.returncode, 0)
        restored = self.run_cli('restore', '--no-reload')
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertFalse((config / 'fontconfig/fonts.conf').exists())

    def test_missing_optional_tools_degrade_instead_of_failing(self):
        """Plasma defaults only: no PyQt6 (Spotlight) and no Kvantum must not break the install."""
        code = (
            "import sys; sys.path.insert(0, %r)\n"
            "import kde\nfrom types import SimpleNamespace\n"
            "kde.qt_launcher_available = lambda: False\nkde.kvantum_available = lambda: False\n"
            "tx = kde.install_files(SimpleNamespace(no_reload=True, skip_panels=True), kde.locations(), kde.configuration())\n"
        ) % str(ROOT / 'lib')
        result = subprocess.run([sys.executable, '-c', code], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('KRunner stays the launcher', result.stderr)
        self.assertFalse((self.home / 'data/applications/darwin-spotlight.desktop').exists())
        self.assertFalse((self.home / 'data/darwin-theme/spotlight').exists())
        kdeglobals = (self.home / 'config/kdeglobals').read_text()
        self.assertNotIn('widgetStyle=kvantum-dark', kdeglobals)   # Breeze stays when Kvantum is absent
        self.assertIn('ColorScheme=DarwinDark', kdeglobals)    # the Plasma-native parts still apply
        self.assertTrue((self.home / 'data/aurorae/themes/Darwin-Dark').is_dir())

    def test_leftovers_of_the_former_name_are_replaced_and_restorable(self):
        data, config = self.home / 'data', self.home / 'config'
        old_dirs = ['aurorae/themes/GoldenGate-Dark', 'plasma/desktoptheme/GoldenGate-Dark', 'kwin/tabbox/GoldenGateDark',
                    'plasma/plasmoids/com.prashantjain25.goldengate.dock', 'icons/GoldenGate-Icons', 'golden-gate-theme/spotlight']
        for rel in old_dirs:
            (data / rel).mkdir(parents=True)
            (data / rel / 'marker.txt').write_text('old ' + rel)
        (data / 'applications').mkdir(parents=True)
        (data / 'applications/golden-gate-spotlight.desktop').write_text('[Desktop Entry]\nName=Old\n')
        (data / 'color-schemes').mkdir(parents=True)
        (data / 'color-schemes/GoldenGateDark.colors').write_text('[General]\nName=Old\n')
        (config / 'gtk-3.0').mkdir(parents=True)
        (config / 'gtk-3.0/gtk.css').write_text('/* mine */\n\n/* BEGIN GOLDEN GATE KDE */\nold {}\n/* END GOLDEN GATE KDE */\n')
        (config / 'kwinrc').write_text('[Plugins]\ngolden-gate-spotlight-positionEnabled=true\nblurEnabled=true\n')
        result = self.run_cli('install', '--no-reload', '--skip-panels')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Removed leftovers of the former name', result.stdout)
        for rel in old_dirs + ['applications/golden-gate-spotlight.desktop', 'color-schemes/GoldenGateDark.colors']:
            self.assertFalse((data / rel).exists(), rel + ' should have been removed')
        css = (config / 'gtk-3.0/gtk.css').read_text()
        self.assertNotIn('GOLDEN GATE', css)          # the old managed block is replaced, not duplicated
        self.assertEqual(css.count('BEGIN DARWIN KDE'), 1)
        self.assertIn('/* mine */', css)
        self.assertNotIn('golden-gate-spotlight-positionEnabled', (config / 'kwinrc').read_text())
        self.assertTrue((data / 'aurorae/themes/Darwin-Dark').is_dir())
        self.assertTrue((data / 'plasma/plasmoids/com.prashantjain25.darwin.dock/metadata.json').is_file())
        self.assertTrue((data / 'color-schemes/DarwinDark.colors').is_file())
        restored = self.run_cli('restore', '--no-reload')
        self.assertEqual(restored.returncode, 0, restored.stderr)
        for rel in old_dirs:
            self.assertEqual((data / rel / 'marker.txt').read_text(), 'old ' + rel)   # the old install is back, exactly
        self.assertIn('BEGIN GOLDEN GATE KDE', (config / 'gtk-3.0/gtk.css').read_text())
        self.assertIn('golden-gate-spotlight-positionEnabled=true', (config / 'kwinrc').read_text())
        self.assertFalse((data / 'aurorae/themes/Darwin-Dark').exists())

    def test_backups_made_under_the_former_name_can_still_be_restored(self):
        old = self.home / 'state/golden-gate-theme/kde/backups/20200101T000000-abcd1234'
        old.mkdir(parents=True)
        target = self.home / 'config/kdeglobals'
        target.parent.mkdir(parents=True)
        (old / '0').write_text('original\n')
        roots = {'config': str(self.home / 'config'), 'data': str(self.home / 'data'), 'state': str(self.home / 'state')}
        (old / 'manifest.json').write_text(json.dumps({'version': 1, 'status': 'active', 'roots': roots,
                                                       'entries': [{'target': str(target), 'backup': '0', 'existed': True}]}))
        target.write_text('changed by the theme\n')
        status = self.run_cli('status')
        self.assertIn('golden-gate-theme/kde/backups/20200101T000000-abcd1234', status.stdout)
        result = self.run_cli('restore', '--no-reload')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), 'original\n')
        self.assertEqual(json.loads((old / 'manifest.json').read_text())['status'], 'restored')

    def test_the_short_lived_darwinosx_install_is_also_cleaned_up(self):
        data = self.home / 'data'
        old = ['aurorae/themes/DarwinOSX-Dark', 'plasma/plasmoids/com.prashantjain25.darwinosx.dock', 'kwin/tabbox/DarwinOSXDark',
               'icons/DarwinOSX-Icons', 'darwin-osx-theme/spotlight']
        for rel in old:
            (data / rel).mkdir(parents=True)
        result = self.run_cli('install', '--no-reload', '--skip-panels')
        self.assertEqual(result.returncode, 0, result.stderr)
        for rel in old:
            self.assertFalse((data / rel).exists(), rel)
        self.assertTrue((data / 'aurorae/themes/Darwin-Dark').is_dir())
        self.assertTrue((data / 'plasma/plasmoids/com.prashantjain25.darwin.dock/metadata.json').is_file())

    def test_tool_checks_never_walk_whole_library_folders(self):
        """A recursive search of /usr/lib took seconds per process and stalled CI; keep the checks targeted."""
        import glob
        import importlib.util
        import time
        spec = importlib.util.spec_from_file_location('kde_under_test', ROOT / 'lib/kde.py')
        sys.path.insert(0, str(ROOT / 'lib'))
        kde = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kde)
        calls, real = [], glob.glob
        glob.glob = lambda *a, **k: calls.append(k.get('recursive')) or real(*a, **k)
        try:
            started = time.monotonic()
            kde.rounded_effect_installed.__wrapped__()
            kde.kvantum_available.__wrapped__()
            elapsed = time.monotonic() - started
        finally:
            glob.glob = real
        self.assertTrue(calls, 'the checks should search for the plugins')
        self.assertNotIn(True, calls, 'recursive searches are too slow')
        self.assertLess(elapsed, 1.0)

    def test_missing_gnome_schema_skips_gtk_live_settings_instead_of_failing(self):
        code = (
            "import sys; sys.path.insert(0, %r)\n"
            "import kde\n"
            "kde.gtk_settings_available = lambda: False\n"
            "kde.shutil.which = lambda name: '/usr/bin/gsettings' if name == 'gsettings' else None\n"
            "kde.apply_runtime(None, kde.configuration())\n"   # a Transaction is not needed when nothing is written
        ) % str(ROOT / 'lib')
        result = subprocess.run([sys.executable, '-c', code], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('GTK live settings were skipped', result.stderr)

    def test_install_rejects_symlink_parents_and_preserves_original_dotfiles(self):
        for root, parent, filename in [('config', 'gtk-3.0', 'settings.ini'),
                                       ('data', 'color-schemes', 'DarwinDark.colors')]:
            with self.subTest(root=root):
                case = self.home / root
                self.env.update({env: str(case / name) for env, name in [
                    ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state')]})
                base = case / root
                base.mkdir(parents=True)
                external = self.home / ('external-' + root)
                external.mkdir()
                original = b'# original external dotfile\n[Settings]\ncustom=value\n'
                (external / filename).write_bytes(original)
                (base / parent).symlink_to(external, target_is_directory=True)
                config = case / 'config'
                config.mkdir(exist_ok=True)
                globals_original = b'# original KDE preferences\n[General]\nfont=My Font,10\n'
                (config / 'kdeglobals').write_bytes(globals_original)
                result = self.run_cli('install', '--no-reload', '--skip-panels')
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Unsafe', result.stderr)
                self.assertEqual((external / filename).read_bytes(), original)
                self.assertEqual((config / 'kdeglobals').read_bytes(), globals_original)
                self.assertFalse((config / 'kwinrc').exists())
                self.assertFalse((case / 'data/aurorae/themes/Darwin-Dark').exists())
                (base / parent).unlink()

    def test_restore_prevalidates_every_target_before_changing_any_file(self):
        for kind in ('outside', 'symlink-parent', 'symlink-target'):
            with self.subTest(kind=kind):
                case = self.home / kind
                config = case / 'config'
                config.mkdir(parents=True)
                external = case / 'external'
                external.mkdir()
                original = b'original external dotfile\n'
                (external / 'settings.ini').write_bytes(original)
                if kind == 'outside':
                    unsafe = external / 'settings.ini'
                elif kind == 'symlink-parent':
                    (config / 'gtk-3.0').symlink_to(external, target_is_directory=True)
                    unsafe = config / 'gtk-3.0/settings.ini'
                else:
                    unsafe = config / 'settings.ini'
                    unsafe.symlink_to(external / 'settings.ini')
                safe = config / 'kdeglobals'
                safe.write_bytes(b'current KDE preferences\n')
                backup = case / 'backup'
                backup.mkdir()
                (backup / '0').write_bytes(b'old unsafe content\n')
                (backup / '1').write_bytes(b'old KDE preferences\n')
                self.env.update({env: str(case / name) for env, name in [
                    ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state')]})
                manifest = {'version': 1, 'status': 'active',
                            'roots': {key: str(case / key) for key in ('config', 'data', 'state')},
                            'entries': [{'target': str(unsafe), 'backup': '0', 'existed': True},
                                        {'target': str(safe), 'backup': '1', 'existed': True}]}
                manifest_path = backup / 'manifest.json'
                manifest_path.write_text(json.dumps(manifest))
                result = self.run_cli('restore', '--no-reload', '--backup', str(backup))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(safe.read_bytes(), b'current KDE preferences\n')
                self.assertEqual((external / 'settings.ini').read_bytes(), original)
                self.assertEqual(json.loads(manifest_path.read_text()), manifest)

    def test_restore_prevalidates_every_backup_source_before_changing_any_file(self):
        for kind in ('missing', 'traversal', 'absolute', 'symlink', 'symlink-parent',
                     'backup-root', 'absent-target-traversal'):
            with self.subTest(kind=kind):
                case = self.home / kind
                config = case / 'config'
                config.mkdir(parents=True)
                target = config / 'settings.ini'
                target.write_bytes(b'current GTK preferences\n')
                safe = config / 'kdeglobals'
                safe.write_bytes(b'current KDE preferences\n')
                external = case / 'external'
                external.mkdir()
                (external / 'original').write_bytes(b'external original\n')
                backup = case / 'backup'
                backup.mkdir()
                (backup / '1').write_bytes(b'old KDE preferences\n')
                source = 'missing'
                if kind in ('traversal', 'absent-target-traversal'):
                    source = '../external/original'
                elif kind == 'absolute':
                    source = str(external / 'original')
                elif kind == 'symlink':
                    source = '0'
                    (backup / source).symlink_to(external / 'original')
                elif kind == 'symlink-parent':
                    source = 'linked/original'
                    (backup / 'linked').symlink_to(external, target_is_directory=True)
                elif kind == 'backup-root':
                    source = '.'
                existed = kind != 'absent-target-traversal'
                self.env.update({env: str(case / name) for env, name in [
                    ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state')]})
                manifest = {'version': 1, 'status': 'active',
                            'roots': {key: str(case / key) for key in ('config', 'data', 'state')},
                            'entries': [{'target': str(target), 'backup': source, 'existed': existed},
                                        {'target': str(safe), 'backup': '1', 'existed': True}]}
                manifest_path = backup / 'manifest.json'
                manifest_path.write_text(json.dumps(manifest))
                result = self.run_cli('restore', '--no-reload', '--backup', str(backup))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(safe.read_bytes(), b'current KDE preferences\n')
                self.assertEqual(target.read_bytes(), b'current GTK preferences\n')
                self.assertEqual((external / 'original').read_bytes(), b'external original\n')
                self.assertEqual(json.loads(manifest_path.read_text()), manifest)

    def test_invalid_kde_configuration_leaves_home_untouched(self):
        cfg = self.home / 'theme.json'
        cfg.write_text(json.dumps({'mode': 'light'}))
        self.env['THEME_CONFIG'] = str(cfg)
        result = self.run_cli('install', '--no-reload', '--skip-panels')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('dark', result.stderr.lower())
        self.assertEqual(list(self.home.iterdir()), [cfg])

    def test_configuration_normalizes_shared_dock_aliases_before_dry_run(self):
        cfg = self.home / 'theme.json'
        self.env['THEME_CONFIG'] = str(cfg)
        for alias, canonical, hiding in [('autohide', 'auto-hide', 'autohide'),
                                         ('intelligent', 'intelligent-hide', 'dodgewindows')]:
            with self.subTest(alias=alias):
                cfg.write_text(json.dumps({'dock': {'mode': alias}}))
                program = '''
import sys
sys.path.insert(0, str(__import__('pathlib').Path.cwd() / 'lib'))
import kde
print(kde.configuration()['dock']['mode'])
'''
                result = subprocess.run([sys.executable, '-c', program], cwd=ROOT, env=self.env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), canonical)
                result = self.run_cli('dock', '--dry-run')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('"hiding": "' + hiding + '"', result.stdout)
                result = self.run_cli('install', '--dry-run', '--no-reload')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(list(self.home.iterdir()), [cfg])

    def test_layout_normalizes_shared_dock_aliases_for_direct_callers(self):
        program = '''
import json
import sys
sys.path.insert(0, str(__import__('pathlib').Path.cwd() / 'lib'))
import kde
cfg = kde.configuration()
for alias, hiding in [('autohide', 'autohide'), ('intelligent', 'dodgewindows')]:
    for override in (False, True):
        cfg['dock']['mode'] = 'reserve' if override else alias
        script = kde.layout_script(cfg, dock_mode=alias if override else None)
        options = json.loads(script.split(' = ', 1)[1].split(';', 1)[0])
        assert options['hiding'] == hiding, options
        assert cfg['dock']['mode'] == ('reserve' if override else alias), cfg
'''
        result = subprocess.run([sys.executable, '-c', program], cwd=ROOT, env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_dock_dry_run_uses_native_plasma_only(self):
        result = self.run_cli('dock', '--dry-run', '--dock-mode', 'intelligent-hide')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('dodgewindows', result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_live_gtk_font_settings_round_trip_with_real_keyfile_backend(self):
        import shutil
        if not shutil.which('gsettings'):
            self.skipTest('gsettings not installed')
        if 'org.gnome.desktop.interface' not in subprocess.run(['gsettings', 'list-schemas'], capture_output=True, text=True).stdout.split():
            self.skipTest('GNOME interface settings schema not installed')
        self.env['GSETTINGS_BACKEND'] = 'keyfile'
        program = '''
import sys
sys.path.insert(0, str(__import__('pathlib').Path.cwd() / 'lib'))
import kde
cfg = kde.configuration()
p = kde.locations()
before = kde.run_checked(['gsettings','get','org.gnome.desktop.interface','font-name'])
tx = kde.Transaction(p)
kde.apply_runtime(tx, cfg)
after = kde.run_checked(['gsettings','get','org.gnome.desktop.interface','font-name'])
assert after == "'Inter 10'", after
kde.restore_backup(tx.directory, p)
assert kde.run_checked(['gsettings','get','org.gnome.desktop.interface','font-name']) == before
'''
        result = subprocess.run([sys.executable, '-c', program], cwd=ROOT, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_panel_readiness_waits_for_persisted_panels_before_creation(self):
        config = self.home / 'config'
        config.mkdir()
        (config / 'plasma-org.kde.plasma.desktop-appletsrc').write_text(
            '[Containments][10]\nplugin=org.kde.panel\nlastScreen=0\n\n'
            '[Containments][20]\nplugin=org.kde.panel\nlastScreen=0\n')
        program = '''
import sys
sys.path.insert(0, str(__import__('pathlib').Path.cwd() / 'lib'))
import kde
counts = iter(['1', '2'])
calls = []
def fake_query(command):
    calls.append(command)
    return next(counts)
kde.run_checked = fake_query
kde.wait_for_panels(kde.locations())
assert len(calls) == 2, calls
'''
        result = subprocess.run([sys.executable, '-c', program], cwd=ROOT, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_live_install_does_not_preempt_theme_apply_notifications(self):
        config = self.home / 'config'
        config.mkdir()
        (config / 'kdeglobals').write_text('[General]\nColorScheme=Before\n')
        (config / 'plasmarc').write_text('[Theme]\nname=Before\n')
        program = '''
import sys
from types import SimpleNamespace
sys.path.insert(0, str(__import__('pathlib').Path.cwd() / 'lib'))
import kde
# This seam only discovers the optional effect; never contact a real compositor in tests.
kde.subprocess.run=lambda *a,**kw:SimpleNamespace(stdout='',returncode=0)
p=kde.locations()
tx=kde.install_files(SimpleNamespace(no_reload=False,skip_panels=True),p,kde.configuration())
assert 'ColorScheme=Before' in (p['config']/'kdeglobals').read_text()
assert 'name=Before' in (p['config']/'plasmarc').read_text()
kde.restore_backup(tx.directory,p)
'''
        result = subprocess.run([sys.executable, '-c', program], cwd=ROOT, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dry_run_explains_changes_without_creating_files(self):
        result = self.run_cli('install', '--dry-run', '--no-reload')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Darwin-Dark', result.stdout)
        self.assertIn('backup', result.stdout.lower())
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
