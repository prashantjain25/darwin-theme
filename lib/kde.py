#!/usr/bin/env python3
"""User-local Darwin KDE theme manager (Python standard library only)."""
import argparse
import functools
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kde_components  # noqa: E402

DOCK_PLASMOID = 'com.prashantjain25.darwin.dock'
# Same prerequisites as the LXQt path: WhiteSur GTK theme + WhiteSur icons, Inter and Maple Mono NF.
WHITESUR = {'dark': ('WhiteSur-Dark', 'WhiteSur-dark'), 'light': ('WhiteSur-Light', 'WhiteSur-light')}
MAPLE_URL = 'https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMono-NF.zip'
MAPLE_SHA256 = '59098b87c895d871635d37680e88000ae2b2b25b55428195b228ec589e35fb89'
TRAY_SHOWN = ['org.kde.plasma.networkmanagement', 'org.kde.plasma.bluetooth', 'org.kde.plasma.volume',
              'org.kde.plasma.devicenotifier']
GSETTINGS_KEYS = ('font-name', 'color-scheme', 'gtk-theme', 'icon-theme', 'monospace-font-name')
SPOTLIGHT_ENTRIES = [('darwin-spotlight.desktop', 'apps', 'Darwin Spotlight'),
                     ('darwin-spotlight-files.desktop', 'files', 'Darwin Spotlight Files'),
                     ('darwin-spotlight-calc.desktop', 'calc', 'Darwin Spotlight Calculator')]
DOCK_MODES = {'reserve': 'none', 'always-on-top': 'windowsgobelow',
              'intelligent-hide': 'dodgewindows', 'auto-hide': 'autohide'}


def configuration():
    # Share the original LXQt configuration loader without invoking X11 resolve().
    from theme import load, norm_mode, validate
    cfg = load()
    errors = validate(cfg)
    if errors:
        raise ValueError('; '.join(errors))
    if cfg['mode'] != 'dark':
        raise ValueError('KDE currently supports the verified dark profile only; set mode to dark.')
    cfg['dock']['mode'] = norm_mode(cfg['dock']['mode'])
    return cfg


def start_icon(cfg):
    """WhiteSur's own start-here.svg (the Apple glyph), by path so the active icon theme cannot replace it."""
    paths = locations()
    name = WHITESUR[cfg['mode']][1]
    for root in (paths['data'] / 'icons', Path.home() / '.icons', Path('/usr/share/icons')):
        candidate = root / name / 'places/16/start-here.svg'
        if candidate.is_file():
            return str(candidate)
    return ''


@functools.lru_cache(maxsize=None)
def screen_scale():
    """Primary screen logical width / 1512 (the Figma frame), as the LXQt dock does."""
    try:
        out = subprocess.run(['kscreen-doctor', '-j'], capture_output=True, text=True, timeout=10).stdout
        outputs = [o for o in json.loads(out).get('outputs', []) if o.get('enabled')]
        primary = min(outputs, key=lambda o: o.get('priority', 99))
        return (primary['size']['width'] / (primary.get('scale') or 1)) / 1512
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return 1.0


def dock_metrics(cfg, zoom=1.55):
    """Icon size and panel height from one Figma unit (icon / 36), identical to Dock.qml."""
    icon = round(cfg['dock']['icon_size'] * screen_scale())
    unit = icon / 36
    glass = round(62 * unit)
    return icon, -(-(glass + icon * (zoom - 1) + 6) // 1)


def layout_script(cfg, menubar=True, dock=True, dock_mode=None):
    from theme import norm_mode
    metrics = dock_metrics(cfg)
    options = {'menubar': menubar and cfg['menubar']['enabled'],
               'dock': dock and cfg['dock']['enabled'],
               'barHeight': cfg['menubar']['height'], 'font': cfg['fonts']['ui'],
               'hiding': DOCK_MODES[norm_mode(dock_mode or cfg['dock']['mode'])],
               'dockIcon': metrics[0], 'dockHeight': int(metrics[1]),
               'startIcon': start_icon(cfg),
               'dockWidget': DOCK_PLASMOID if (locations()['data'] / 'plasma/plasmoids' / DOCK_PLASMOID / 'metadata.json').is_file() else ''}
    return 'var DARWIN_OPTIONS = ' + json.dumps(options) + ';\n' + (ROOT / 'assets/layout.js').read_text()


def locations():
    home = Path.home()
    return {name: Path(os.environ.get(env, home / default)).expanduser()
            for name, env, default in [
                ('config', 'XDG_CONFIG_HOME', '.config'),
                ('data', 'XDG_DATA_HOME', '.local/share'),
                ('state', 'XDG_STATE_HOME', '.local/state')]}


def merge_ini(text, section, updates):
    """Change explicit keys only, preserving comments, other keys and KConfig nesting."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line == f'[{section}]'), None)
    if start is None:
        if lines and lines[-1]:
            lines.append('')
        lines += [f'[{section}]']
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('[')), len(lines))
    pending = dict(updates)
    for i in range(start + 1, end):
        key = lines[i].partition('=')[0]
        if key in pending:
            lines[i] = f'{key}={pending.pop(key)}'
    lines[end:end] = [f'{key}={value}' for key, value in pending.items()]
    return '\n'.join(lines) + '\n'


# Pieces installed under the project's former name (Golden Gate). They are backed up and removed on install,
# so a renamed theme never leaves two copies behind. The old dock widget goes last, after its pins move.
LEGACY_DATA = ['aurorae/themes/GoldenGate-Dark', 'plasma/desktoptheme/GoldenGate-Dark', 'color-schemes/GoldenGateDark.colors',
               'plasma/look-and-feel/com.prashantjain25.goldengate.dark', 'Kvantum/GoldenGateDark', 'kwin/tabbox/GoldenGate',
               'kwin/tabbox/GoldenGateDark', 'icons/GoldenGate-Icons', 'kwin/scripts/golden-gate-spotlight-position',
               'applications/golden-gate-spotlight.desktop', 'applications/golden-gate-spotlight-files.desktop',
               'applications/golden-gate-spotlight-calc.desktop', 'golden-gate-theme/spotlight', 'fonts/golden-gate']
LEGACY_DATA += ['aurorae/themes/DarwinOSX-Dark', 'plasma/desktoptheme/DarwinOSX-Dark', 'color-schemes/DarwinOSXDark.colors',
                'plasma/look-and-feel/com.prashantjain25.darwinosx.dark', 'Kvantum/DarwinOSXDark', 'kwin/tabbox/DarwinOSX',
                'kwin/tabbox/DarwinOSXDark', 'icons/DarwinOSX-Icons', 'kwin/scripts/darwin-osx-spotlight-position',
                'applications/darwin-osx-spotlight.desktop', 'applications/darwin-osx-spotlight-files.desktop',
                'applications/darwin-osx-spotlight-calc.desktop', 'darwin-osx-theme/spotlight', 'fonts/darwin-osx']
LEGACY_CONFIG = ['Kvantum/GoldenGateDark', 'Kvantum/DarwinOSXDark']
LEGACY_PLASMOIDS = ['plasma/plasmoids/com.prashantjain25.goldengate.dock', 'plasma/plasmoids/com.prashantjain25.darwinosx.dock']
LEGACY_CSS_MARKERS = (('/* BEGIN GOLDEN GATE KDE */', '/* END GOLDEN GATE KDE */'), ('/* BEGIN DARWIN OSX KDE */', '/* END DARWIN OSX KDE */'))


def remove_legacy(tx, paths, plasmoid=False):
    """Back up, then delete, leftovers of the old name. Anything missing is simply skipped."""
    targets = [paths['data'] / rel for rel in LEGACY_DATA] + [paths['config'] / rel for rel in LEGACY_CONFIG]
    if plasmoid:
        targets += [paths['data'] / rel for rel in LEGACY_PLASMOIDS]
    removed = []
    for target in targets:
        if target.is_symlink() or not target.exists():
            continue
        tx.capture(target)
        shutil.rmtree(target) if target.is_dir() else target.unlink()
        removed.append(target.name)
    kwinrc = paths['config'] / 'kwinrc'
    old_keys = ('golden-gate-spotlight-positionEnabled=', 'darwin-osx-spotlight-positionEnabled=')
    if kwinrc.exists() and any(key in kwinrc.read_text() for key in old_keys):
        tx.write(kwinrc, ''.join(line for line in kwinrc.read_text().splitlines(True) if not line.startswith(old_keys)))
    if removed:
        print('Removed leftovers of the former name: ' + ', '.join(removed))


def managed_css(text, css):
    begin, end = '/* BEGIN DARWIN KDE */', '/* END DARWIN KDE */'
    for first, last in ((begin, end), *LEGACY_CSS_MARKERS):
        text = re.sub(re.escape(first) + r'.*?' + re.escape(last) + r'\n?', '', text, flags=re.S)
    return text.rstrip() + '\n\n' + begin + '\n' + css.rstrip() + '\n' + end + '\n'


def validate_target(target, paths):
    roots = [paths['config'].resolve(), paths['data'].resolve()]
    if not any(target.resolve().is_relative_to(root) for root in roots):
        raise ValueError(f'Unsafe backup target: {target}')
    if target.is_symlink():
        raise ValueError(f'Refusing symbolic-link target: {target}')


class Transaction:
    """Private, exact file/tree backups; a restore never fetches or runs remote code."""
    def __init__(self, paths):
        self.paths = paths
        self.directory = paths['state'] / 'darwin-theme/kde/backups' / (
            datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
        self.directory.mkdir(parents=True, mode=0o700)
        self.entries = []
        self.save()

    def save(self):
        manifest = {'version': 1, 'status': 'active', 'roots': {k: str(v) for k, v in self.paths.items()},
                    'entries': self.entries}
        path = self.directory / 'manifest.json'
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        path.chmod(0o600)

    def capture(self, target):
        target = Path(target)
        validate_target(target, self.paths)
        if any(e['target'] == str(target) for e in self.entries):
            return
        backup = str(len(self.entries))
        exists = target.exists()
        if exists:
            if target.is_dir():
                shutil.copytree(target, self.directory / backup, symlinks=True)
            else:
                shutil.copy2(target, self.directory / backup)
        self.entries.append({'target': str(target), 'backup': backup, 'existed': exists})
        self.save()

    def write(self, target, text):
        self.capture(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.darwin-new')
        temporary.write_text(text)
        if target.exists():
            shutil.copymode(target, temporary)
        else:
            temporary.chmod(0o600)
        temporary.replace(target)

    def copy(self, source, target):
        self.capture(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.in'))
        else:
            shutil.copy2(source, target)


def restore_backup(directory, paths):
    manifest_path = directory / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('roots') != {k: str(v) for k, v in paths.items()}:
        raise ValueError('Backup belongs to different XDG directories; restore in its original environment.')
    for entry in manifest['entries']:
        validate_target(Path(entry['target']), paths)
        source = directory / entry['backup']
        resolved = source.resolve()
        if resolved == directory.resolve() or not resolved.is_relative_to(directory.resolve()) or source.is_symlink():
            raise ValueError(f'Unsafe backup source: {source}')
        if entry['existed'] and not (source.is_file() or source.is_dir()):
            raise ValueError(f'Missing or invalid backup source: {source}')
    for entry in reversed(manifest['entries']):
        target = Path(entry['target'])
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        if entry['existed']:
            source = directory / entry['backup']
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            else:
                shutil.copy2(source, target)
    runtime_path = directory / 'runtime.json'
    if runtime_path.exists():
        runtime = json.loads(runtime_path.read_text())
        if runtime.get('shortcuts') and shutil.which('gdbus'):
            kde_components.restore_spotlight_shortcuts(runtime, run_checked)
        for key, value in runtime.get('gsettings', {}).items():
            if key not in GSETTINGS_KEYS:
                raise ValueError(f'Unexpected GTK runtime setting: {key}')
            run_checked(['gsettings', 'set', 'org.gnome.desktop.interface', key, value])
    manifest['status'] = 'restored'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Restored: {directory}')


ROUNDED_URL = 'https://github.com/matinlotfali/KDE-Rounded-Corners.git'
ROUNDED_TAG = 'v0.7.2'
ROUNDED_APT = ['git', 'cmake', 'g++', 'extra-cmake-modules', 'kwin-dev', 'qt6-base-private-dev', 'qt6-base-dev-tools',
               'libkf6kcmutils-dev', 'gettext']


@functools.lru_cache(maxsize=None)
def rounded_effect_installed():
    """The KWin effect that rounds the bottom window corners (Aurorae already rounds the top).

    Only the usual plugin folders are checked. A recursive search of /usr/lib takes seconds, which made
    every start slow on systems without the effect.
    """
    import glob
    name = 'qt6/plugins/kwin/effects/plugins/kwin4_effect_shapecorners.so'
    roots = ['/usr/lib*', '/usr/lib*/*', '/usr/local/lib*', '/usr/local/lib*/*', str(Path.home() / '.local/lib*'), str(Path.home() / '.local/lib*/*')]
    return any(glob.glob(f'{root}/{name}') for root in roots)


def install_rounded_effect(args):
    """Build the pinned KDE-Rounded-Corners release when --install-deps is given (needs sudo + network)."""
    if rounded_effect_installed():
        return True
    if not getattr(args, 'install_deps', False):
        print('Note: the KWin rounded-corners effect is not installed, so only the top window corners are rounded. '
              'Run ./install.sh --install-deps to build KDE-Rounded-Corners ' + ROUNDED_TAG + '.', file=sys.stderr)
        return False
    release = Path('/etc/os-release').read_text().lower() if Path('/etc/os-release').exists() else ''
    if not re.search(r'\b(debian|ubuntu)\b', release):
        print('Note: automatic build is only provided for Debian/Ubuntu/Kubuntu. Install KDE-Rounded-Corners manually: '
              + ROUNDED_URL.removesuffix('.git') + ' (see its README for your distribution).', file=sys.stderr)
        return False
    import tempfile
    try:
        print('Installing build packages and building KDE-Rounded-Corners ' + ROUNDED_TAG + ' (sudo is needed) ...')
        subprocess.run(['sudo', 'apt-get', 'install', '-y', *ROUNDED_APT], check=True, timeout=1800)
        with tempfile.TemporaryDirectory() as work:
            subprocess.run(['git', 'clone', '--depth', '1', '--branch', ROUNDED_TAG, ROUNDED_URL, work + '/src'], check=True, timeout=600)
            subprocess.run(['cmake', '-S', work + '/src', '-B', work + '/build', '-DCMAKE_BUILD_TYPE=Release'], check=True, timeout=600)
            subprocess.run(['cmake', '--build', work + '/build', '-j'], check=True, timeout=3600)
            subprocess.run(['sudo', 'cmake', '--install', work + '/build'], check=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as error:
        print(f'Warning: could not build the rounded-corners effect ({error}).', file=sys.stderr)
    rounded_effect_installed.cache_clear()
    return rounded_effect_installed()


def find_gtk_theme(paths, name):
    for root in (Path.home() / '.themes', paths['data'] / 'themes', Path('/usr/share/themes')):
        if (root / name / 'gtk-3.0').is_dir():
            return True
    return False


def find_icon_theme(paths, name):
    for root in (paths['data'] / 'icons', Path.home() / '.icons', Path('/usr/share/icons')):
        if (root / name / 'index.theme').is_file():
            return True
    return False


@functools.lru_cache(maxsize=None)
def qt_launcher_available():
    """The Spotlight launcher needs PyQt6; without it KRunner (Plasma's own launcher) is used instead."""
    try:
        return subprocess.run(['/usr/bin/python3', '-c', 'import PyQt6.QtWidgets, PyQt6.QtNetwork'],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@functools.lru_cache(maxsize=None)
def kvantum_available():
    import glob
    return bool(shutil.which('kvantummanager')) or any(glob.glob(f'{root}/qt6/plugins/styles/libkvantum.so') for root in ('/usr/lib*', '/usr/lib*/*'))


@functools.lru_cache(maxsize=None)
def font_installed(family):
    try:
        out = subprocess.run(['fc-list', ':', 'family'], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return any(family.lower() == part.strip().lower() for line in out.splitlines() for part in line.split(','))


def install_prerequisites(args, paths, cfg):
    """WhiteSur GTK/icons through the same helpers the LXQt path uses (git clone + upstream installer)."""
    gtk, icons = WHITESUR[cfg['mode']]
    missing = [n for n, ok in ((gtk + ' GTK theme', find_gtk_theme(paths, gtk)), (icons + ' icon theme', find_icon_theme(paths, icons))) if not ok]
    if missing and getattr(args, 'install_deps', False):
        script = (f'source "{ROOT}/lib/common.sh"; INSTALL_DEPS=1; ensure_whitesur_gtk {gtk}; ensure_whitesur_icons')
        result = subprocess.run(['bash', '-c', script], text=True, timeout=900)
        if result.returncode:
            print('Warning: WhiteSur installation did not finish; continuing without it.', file=sys.stderr)
    elif missing:
        print('Missing: ' + ', '.join(missing) + '. Run ./install.sh --install-deps to fetch them '
              '(github.com/vinceliuice/WhiteSur-gtk-theme and WhiteSur-icon-theme).', file=sys.stderr)


def install_maple(tx, paths, args):
    """Download the pinned Maple Mono NF release (checksum verified) into the user font directory."""
    if not getattr(args, 'install_deps', False) or font_installed('Maple Mono NF'):
        return
    import io
    try:
        with urllib.request.urlopen(MAPLE_URL, timeout=120) as response:
            blob = response.read()
        if hashlib.sha256(blob).hexdigest() != MAPLE_SHA256:
            raise ValueError('Maple Mono checksum mismatch')
        target = paths['data'] / 'fonts/MapleMono-NF'
        tx.capture(target)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            for name in archive.namelist():
                if name.endswith('.ttf') and '/' not in name.strip('/'):
                    (target / Path(name).name).write_bytes(archive.read(name))
        subprocess.run(['fc-cache', str(target)], capture_output=True)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f'Warning: Maple Mono NF not installed ({error}).', file=sys.stderr)


def install_spotlight_entries(tx, data):
    template = (ROOT / 'assets/spotlight/darwin-spotlight.desktop.in').read_text()
    script = kde_components.desktop_quote(str(data / 'darwin-theme/spotlight/spotlight.py'))
    text = template.replace('@SPOTLIGHT_SCRIPT@', script)
    for filename, mode, name in SPOTLIGHT_ENTRIES:
        if mode == 'apps':
            entry = text
        else:
            entry = text.split('\n[Desktop Action', 1)[0]
            entry = re.sub(r'\nActions=[^\n]*', '', entry)
            entry = entry.replace('Name=Darwin Spotlight', 'Name=' + name, 1).replace('--mode apps', '--mode ' + mode)
        tx.write(data / 'applications' / filename, entry if entry.endswith('\n') else entry + '\n')


def ini_change(tx, target, section, updates):
    tx.write(target, merge_ini(target.read_text() if target.exists() else '', section, updates))


def install_files(args, paths, cfg):
    install_prerequisites(args, paths, cfg)
    rounded = install_rounded_effect(args)
    tx = Transaction(paths)
    remove_legacy(tx, paths, plasmoid=getattr(args, 'no_reload', False))
    config, data = paths['config'], paths['data']
    gtk_theme, icon_theme = WHITESUR[cfg['mode']]
    have_gtk, have_icons = find_gtk_theme(paths, gtk_theme), find_icon_theme(paths, icon_theme)
    have_qt, have_kvantum = qt_launcher_available(), kvantum_available()
    mono = cfg['fonts']['mono']
    tabbox_name = 'DarwinDark' if cfg['mode'] == 'dark' else 'Darwin'
    try:
        for source, destination in [
            ('aurorae/Darwin-Dark', 'aurorae/themes/Darwin-Dark'),
            ('plasma/Darwin-Dark', 'plasma/desktoptheme/Darwin-Dark'),
            ('color-schemes/DarwinDark.colors', 'color-schemes/DarwinDark.colors'),
            ('look-and-feel/com.prashantjain25.darwin.dark', 'plasma/look-and-feel/com.prashantjain25.darwin.dark'),
            ('kvantum/DarwinDark', 'Kvantum/DarwinDark'),
            ('fonts/Inter', 'fonts/darwin/Inter'),
            ('icons/Darwin-Icons', 'icons/Darwin-Icons'),
            ('tabbox/Darwin', 'kwin/tabbox/Darwin'),
            ('plasmoids/' + DOCK_PLASMOID, 'plasma/plasmoids/' + DOCK_PLASMOID),
            ('kwin-scripts/darwin-spotlight-position', 'kwin/scripts/darwin-spotlight-position'),
            ('spotlight', 'darwin-theme/spotlight')]:
            if not have_qt and 'spotlight' in source:
                continue
            tx.copy(ROOT / 'assets' / source, data / destination)
        if have_qt:
            install_spotlight_entries(tx, data)
        else:
            print('Note: python3-pyqt6 is not installed, so the Darwin Spotlight is skipped; KRunner stays the launcher '
                  '(Meta+Space is given to KRunner).', file=sys.stderr)
        if tabbox_name == 'DarwinDark':
            # KWin caches a switcher's QML by path, so the dark variant is its own package (own layout name).
            target = data / 'kwin/tabbox/DarwinDark'
            tx.copy(ROOT / 'assets/tabbox/Darwin', target)
            view = target / 'contents/ui/DarwinView.qml'
            tx.write(view, view.read_text().replace('property bool dark: false', 'property bool dark: true', 1))
            meta = json.loads((target / 'metadata.json').read_text())
            meta['KPlugin'].update({'Id': 'DarwinDark', 'Name': 'Darwin Dark',
                                    'Description': 'Dark translucent per-window switcher with application labels below the selected icon'})
            tx.write(target / 'metadata.json', json.dumps(meta, indent=2) + '\n')
        install_maple(tx, paths, args)
        # Copy the scheme's explicit palette, not any machine's complete kdeglobals.
        scheme = (ROOT / 'assets/color-schemes/DarwinDark.colors').read_text()
        for match in re.finditer(r'^\[([^\n]+)\]\n([^\[]*)', scheme, re.M):
            section, body = match.groups()
            if section.startswith(('Colors:', 'ColorEffects:')) or section == 'WM':
                updates = dict(line.split('=', 1) for line in body.splitlines() if '=' in line and not line.startswith('#'))
                ini_change(tx, config / 'kdeglobals', section, updates)
        font = cfg['fonts']['ui']
        size = cfg['fonts']['ui_size']
        accent = cfg['accent'] if cfg['accent'] != 'auto' else '#0091ff'
        accent_rgb = ','.join(str(int(accent[i:i + 2], 16)) for i in (1, 3, 5))
        for section, values in {
            'General': {'ColorScheme': 'DarwinDark', 'AccentColor': accent_rgb,
                        'font': f'{font},{size},-1,5,400,0,0,0,0,0,0,0,0,0,0,1', 'menuFont': f'{font},{size},-1,5,400,0,0,0,0,0,0,0,0,0,0,1',
                        'toolBarFont': f'{font},{size},-1,5,400,0,0,0,0,0,0,0,0,0,0,1', 'smallestReadableFont': f'{font},9,-1,5,400,0,0,0,0,0,0,0,0,0,0,1'},
            'KDE': {'LookAndFeelPackage': 'com.prashantjain25.darwin.dark',
                    **({'widgetStyle': 'kvantum-dark'} if have_kvantum else {}), 'ShowIconsInMenuItems': 'false', 'ShowIconsOnPushButtons': 'false'},
            'WM': {'activeFont': f'{font},{cfg["window"]["titlebar_font_size"]},-1,5,500,0,0,0,0,0,0,0,0,0,0,1'},
        }.items():
            if section == 'General' and not args.no_reload:
                values.pop('ColorScheme', None)
            ini_change(tx, config / 'kdeglobals', section, values)
        # Retain the user's icon/cursor choices; use redistributable fallbacks on a fresh desktop.
        globals_text = (config / 'kdeglobals').read_text()
        if have_icons:
            # WhiteSur plus the tray chevrons; every other icon is inherited from WhiteSur.
            ini_change(tx, config / 'kdeglobals', 'Icons', {'Theme': 'Darwin-Icons' if cfg['mode'] == 'dark' else icon_theme})
        elif not re.search(r'^\[Icons\]\n(?:(?!\[).)*^Theme=', globals_text, re.M | re.S):
            ini_change(tx, config / 'kdeglobals', 'Icons', {'Theme': 'breeze-dark'})
        if font_installed(mono):
            ini_change(tx, config / 'kdeglobals', 'General', {'fixed': f'{mono},{size},-1,5,400,0,0,0,0,0,0,0,0,0,0,1'})
        template = (ROOT / 'assets/fontconfig/fonts.conf').read_text().replace('Maple Mono NF', mono)
        tx.write(config / 'fontconfig/fonts.conf', template)
        for section, values in {
            'org.kde.kdecoration2': {'library': 'org.kde.kwin.aurorae.v2', 'theme': '__aurorae__svg__Darwin-Dark',
                                   'ButtonsOnLeft': 'XIA', 'ButtonsOnRight': '', 'BorderSizeAuto': 'false', 'BorderSize': 'Tiny'},
            'Plugins': {'blurEnabled': 'true', **({'darwin-spotlight-positionEnabled': 'true'} if have_qt else {})},
            'TabBox': {'LayoutName': tabbox_name},
        }.items():
            ini_change(tx, config / 'kwinrc', section, values)
        # The effect is optional; configure it whenever its plugin exists (installing it needs --install-deps).
        if rounded:
            radius = str(int(cfg['window']['corner_radius']))
            outline = '255,255,255' if cfg['mode'] == 'dark' else '0,0,0'
            ini_change(tx, config / 'kwinrc', 'Plugins', {'kwin4_effect_shapecornersEnabled': 'true'})
            ini_change(tx, config / 'kwinrc', 'Round-Corners', {
                'ActiveCornerRadius': radius, 'InactiveCornerRadius': radius, 'Size': radius, 'Squircleness': '0',
                'OutlineThickness': '1', 'InactiveOutlineThickness': '1', 'SecondOutlineThickness': '0',
                'InactiveSecondOutlineThickness': '0', 'OutlineColor': outline,
                'InactiveOutlineColor': outline, 'ActiveOutlineAlpha': '70', 'InactiveOutlineAlpha': '50',
                'ActiveOutlineUseCustom': 'true', 'InactiveOutlineUseCustom': 'true',
                'ActiveOutlineUsePalette': 'false', 'InactiveOutlineUsePalette': 'false'})
        ini_change(tx, config / 'auroraerc', 'Darwin-Dark', {'ButtonSize': '1'})
        if args.no_reload:
            ini_change(tx, config / 'plasmarc', 'Theme', {'name': 'Darwin-Dark'})
        else:
            # Let plasma-apply-desktoptheme write this key and notify the running shell.
            tx.capture(config / 'plasmarc')
        if have_kvantum:
            ini_change(tx, config / 'Kvantum/kvantum.kvconfig', 'General', {'theme': 'DarwinDark'})
        else:
            print('Note: Kvantum is not installed; the Breeze widget style is kept (install qt6-style-kvantum for the dark widgets).', file=sys.stderr)
        # A user config wins over the same-named data-dir theme; keep all components together.
        tx.copy(ROOT / 'assets/kvantum/DarwinDark', config / 'Kvantum/DarwinDark')
        for version in ('3', '4'):
            gtk_values = {'gtk-application-prefer-dark-theme': '1', 'gtk-font-name': f'{font} {size}',
                          'gtk-decoration-layout': 'close,minimize,maximize:'}
            if have_gtk:
                gtk_values['gtk-theme-name'] = gtk_theme
            if have_icons:
                gtk_values['gtk-icon-theme-name'] = icon_theme
            ini_change(tx, config / f'gtk-{version}.0/settings.ini', 'Settings', gtk_values)
            target = config / f'gtk-{version}.0/gtk.css'
            tx.write(target, managed_css(target.read_text() if target.exists() else '',
                                        (ROOT / f'assets/gtk/gtk{version}.css').read_text()))
        if not args.skip_panels:
            # Plasma writes these files after scripting; preserve them before the first live call.
            tx.capture(config / 'plasma-org.kde.plasma.desktop-appletsrc')
            tx.capture(config / 'plasmashellrc')
        print(f'Backup: {tx.directory}')
        return tx
    except Exception:
        restore_backup(tx.directory, paths)
        raise


def run_checked(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=40)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout.strip()


def start_plasmashell():
    """Start the shell. Several quick restarts trip systemd's start-rate limit, so clear it first;
    otherwise the user could be left without panels."""
    subprocess.run(['systemctl', '--user', 'reset-failed', 'plasma-plasmashell.service'], capture_output=True)
    run_checked(['systemctl', '--user', 'start', 'plasma-plasmashell.service'])


def wait_for_panels(paths):
    """D-Bus can answer before Plasma has instantiated all persisted panels."""
    import time
    file = paths['config'] / 'plasma-org.kde.plasma.desktop-appletsrc'
    text = file.read_text() if file.exists() else ''
    groups = re.findall(r'^\[Containments\]\[\d+\]\n(.*?)(?=^\[|\Z)', text, re.M | re.S)
    expected = sum('plugin=org.kde.panel' in body and 'lastScreen=-1' not in body for body in groups)
    deadline = time.monotonic() + 15
    while True:
        actual = run_checked(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
                              'org.kde.PlasmaShell.evaluateScript', 'print(panels().length)'])
        if int(actual) >= expected:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f'Plasma is still loading panels ({actual}/{expected}); try again once the desktop is ready.')
        time.sleep(0.2)


def tray_item_ids(hidden_titles, shown_titles=()):
    """Ids of running StatusNotifier (app) items to collapse behind the chevron.

    The reference tray shows only network, Bluetooth, volume and drives, so every app item is hidden unless
    its Title/Id is listed in menubar.shown_tray_items; menubar.hidden_tray_items stay hidden regardless.
    """
    wanted = {t.lower() for t in hidden_titles}
    keep = {t.lower() for t in shown_titles}
    found = []
    try:
        listing = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.kde.StatusNotifierWatcher',
                                  '--object-path', '/StatusNotifierWatcher', '--method', 'org.freedesktop.DBus.Properties.Get',
                                  'org.kde.StatusNotifierWatcher', 'RegisteredStatusNotifierItems'],
                                 capture_output=True, text=True, timeout=10).stdout
        for entry in re.findall(r"'([^']+)'", listing):
            service, _, path = entry.partition('/')
            values = []
            for prop in ('Id', 'Title'):
                out = subprocess.run(['gdbus', 'call', '--session', '--dest', service, '--object-path', '/' + path,
                                      '--method', 'org.freedesktop.DBus.Properties.Get', 'org.kde.StatusNotifierItem', prop],
                                     capture_output=True, text=True, timeout=10).stdout
                match = re.search(r"<'(.*)'>", out)
                values.append(match.group(1) if match else '')
            names = [v.lower() for v in values if v]
            if any(n in wanted for n in names) or not any(n in keep for n in names):
                found.append(values[0])
    except (OSError, subprocess.SubprocessError):
        pass
    return [f for f in found if f]


def configure_panels(tx, paths, cfg):
    """Tray (few icons, the rest behind the chevron) and per-panel background mode.

    Plasma rewrites these files when it exits and ignores scripting for them, so edit them with the
    shell stopped (the files are already in the backup) and start it again.
    """
    applets = paths['config'] / 'plasma-org.kde.plasma.desktop-appletsrc'
    views = paths['config'] / 'plasmashellrc'
    if not shutil.which('systemctl'):
        print('Note: systemctl not found; panel/tray background settings were not applied.', file=sys.stderr)
        return
    original_text = applets.read_text() if applets.exists() else ''
    original_rc = views.read_text() if views.exists() else ''
    text, rc = original_text, original_rc
    sni = tray_item_ids(cfg['menubar'].get('hidden_tray_items', []), cfg['menubar'].get('shown_tray_items', []))
    for match in re.finditer(r'^\[Containments\]\[(\d+)\]\n(.*?)(?=^\[|\Z)', text, re.M | re.S):
        body = match.group(2)
        if 'plugin=org.kde.panel' not in body:
            continue
        location = re.search(r'^location=(\d+)', body, re.M)
        # Top bar keeps the translucent charcoal file; the dock draws its own glass so its panel is fully transparent.
        mode = {'3': '2', '4': '1'}.get(location.group(1) if location else '')
        if mode:
            rc = merge_ini(rc, f'PlasmaViews][Panel {match.group(1)}', {'panelOpacity': mode})
    for match in re.finditer(r'^\[Containments\]\[(\d+)\]\[Applets\]\[(\d+)\]\n(.*?)(?=^\[|\Z)', original_text, re.M | re.S):
        if 'plugin=org.kde.plasma.systemtray' not in match.group(3):
            continue
        section = f'Containments][{match.group(1)}][Applets][{match.group(2)}][General'
        known = re.search(rf'^\[{re.escape(section)}\]\n(?:[^\[]*?\n)*?knownItems=([^\n]*)', original_text, re.M)
        known_items = known.group(1).split(',') if known else []
        hidden = [i for i in dict.fromkeys(known_items + sni) if i and i not in TRAY_SHOWN]
        text = merge_ini(text, section, {'shownItems': ','.join(TRAY_SHOWN), 'hiddenItems': ','.join(hidden)})
    normalize = lambda value: '\n'.join(value.splitlines()) + '\n'
    if normalize(text) == normalize(original_text) and normalize(rc) == normalize(original_rc):
        return   # already configured: leave the running shell alone (saves several seconds and a restart)
    run_checked(['systemctl', '--user', 'stop', 'plasma-plasmashell.service'])
    try:
        tx.write(applets, text)
        tx.write(views, rc)
    finally:
        start_plasmashell()
        wait_for_panels(paths)


def apply_runtime(tx, cfg):
    """Synchronize GTK's live settings provider, with reversible values."""
    if shutil.which('gsettings'):
        gtk_theme, icon_theme = WHITESUR[cfg['mode']]
        values = {'font-name': f"{cfg['fonts']['ui']} {cfg['fonts']['ui_size']}",
                  'color-scheme': 'prefer-dark'}
        paths = locations()
        if find_gtk_theme(paths, gtk_theme):
            values['gtk-theme'] = gtk_theme
        if find_icon_theme(paths, icon_theme):
            values['icon-theme'] = icon_theme
        if font_installed(cfg['fonts']['mono']):
            values['monospace-font-name'] = f"{cfg['fonts']['mono']} {cfg['fonts']['ui_size']}"
        if any(run_checked(['gsettings', 'list-keys', 'org.gnome.desktop.interface']).split().count(k) == 0 for k in values):
            values = {k: v for k, v in values.items() if k in run_checked(['gsettings', 'list-keys', 'org.gnome.desktop.interface']).split()}
        previous = {key: run_checked(['gsettings', 'get', 'org.gnome.desktop.interface', key]) for key in values}
        path = tx.directory / 'runtime.json'
        path.write_text(json.dumps({'gsettings': previous}, indent=2) + '\n')
        path.chmod(0o600)
        for key, value in values.items():
            run_checked(['gsettings', 'set', 'org.gnome.desktop.interface', key, value])
    if shutil.which('dbus-send') and not os.environ.get('GSETTINGS_BACKEND') == 'keyfile':
        run_checked(['dbus-send', '--session', '--type=signal', '/KDEPlatformTheme',
                     'org.kde.KDEPlatformTheme.refreshFonts'])


def theme_digest(accent):
    """Fingerprint of the shipped colour scheme and Plasma theme, to know when re-applying is pointless."""
    digest = hashlib.sha256(accent.encode())
    files = [ROOT / 'assets/color-schemes/DarwinDark.colors', *sorted((ROOT / 'assets/plasma/Darwin-Dark').rglob('*'))]
    for file in files:
        if file.is_file():
            digest.update(file.name.encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()


def theme_already_applied(paths, digest):
    """True when the live scheme/theme names are ours and the shipped files have not changed since last time."""
    stamp = paths['state'] / 'darwin-theme/kde/applied.json'
    try:
        previous = json.loads(stamp.read_text()).get('digest')
        scheme = re.search(r'^ColorScheme=(.*)$', (paths['config'] / 'kdeglobals').read_text(), re.M)
        theme = re.search(r'^name=(.*)$', (paths['config'] / 'plasmarc').read_text(), re.M)
    except (OSError, ValueError, AttributeError):
        return False
    return previous == digest and bool(scheme) and scheme.group(1).strip() == 'DarwinDark' \
        and bool(theme) and theme.group(1).strip() == 'Darwin-Dark'


def reload_desktop(args, cfg, tx):
    accent = cfg['accent'] if cfg['accent'] != 'auto' else '#0091ff'
    paths = locations()
    digest = theme_digest(accent)
    if not theme_already_applied(paths, digest):
        # With --accent-color the tool applies only the accent and ignores the scheme name, so do it in two steps.
        run_checked(['plasma-apply-colorscheme', 'DarwinDark'])
        run_checked(['plasma-apply-colorscheme', '--accent-color', accent])
        run_checked(['plasma-apply-desktoptheme', 'Darwin-Dark'])
        stamp = paths['state'] / 'darwin-theme/kde/applied.json'
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(json.dumps({'digest': digest}) + '\n')
    run_checked(['qdbus6', 'org.kde.KWin', '/KWin', 'reconfigure'])
    if rounded_effect_installed():
        subprocess.run(['qdbus6', 'org.kde.KWin', '/Effects', 'org.kde.kwin.Effects.loadEffect', 'kwin4_effect_shapecorners'], capture_output=True)
    result = subprocess.run(['qdbus6', 'org.kde.KWin', '/Effects',
                             'org.kde.kwin.Effects.reconfigureEffect', 'kwin4_effect_shapecorners'],
                            capture_output=True, text=True)
    if result.returncode:
        print('Optional rounded-corner effect not reconfigured (Aurorae still provides top corners).')
    if not args.skip_panels:
        output = run_checked(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
                              'org.kde.PlasmaShell.evaluateScript', layout_script(cfg)])
        if 'DARWIN_LAYOUT_OK' not in output:
            raise RuntimeError(f'Panel layout did not confirm completion: {output}')
        print(output)
        remove_legacy(tx, paths, plasmoid=True)
        configure_panels(tx, locations(), cfg)
    if shutil.which('gdbus'):
        kde_components.unregister_legacy_shortcuts(subprocess.run)
        rc = paths['config'] / 'kglobalshortcutsrc'
        if rc.exists() and any(name in rc.read_text() for name in kde_components.LEGACY_SERVICES):
            tx.write(rc, kde_components.drop_legacy_sections(rc.read_text()))
        try:
            shortcuts = None if qt_launcher_available() else kde_components.KRUNNER_SHORTCUTS
            for warning in kde_components.register_spotlight_shortcuts(tx, run_checked, shortcuts):
                print('Warning: ' + warning, file=sys.stderr)
        except (RuntimeError, ValueError) as error:
            print(f'Warning: Spotlight shortcuts not fully registered ({error}); restore will undo any partial change.', file=sys.stderr)
    if shutil.which('fc-cache'):
        run_checked(['fc-cache', str(locations()['data'] / 'fonts/darwin')])   # no -f: only rebuilds what changed
    print('Live theme reloaded. Reopen Qt/GTK applications for new fonts/widget style.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    install = sub.add_parser('install', help='Install theme locally with exact backups')
    install.add_argument('--dry-run', action='store_true')
    install.add_argument('--no-reload', action='store_true', help='Write files only; no D-Bus calls')
    install.add_argument('--skip-panels', action='store_true', help='Keep existing panels unchanged')
    install.add_argument('--install-deps', action='store_true', help='Fetch missing WhiteSur GTK/icon themes and Maple Mono NF')
    dock = sub.add_parser('dock', help='Update native Plasma top panel/dock only')
    dock.add_argument('--dry-run', action='store_true')
    dock.add_argument('--no-reload', action='store_true')
    dock.add_argument('--dock-mode', choices=DOCK_MODES)
    exclusive = dock.add_mutually_exclusive_group()
    exclusive.add_argument('--dock-only', action='store_true')
    exclusive.add_argument('--menubar-only', action='store_true')
    restore = sub.add_parser('restore', help='Restore the newest unrestored backup')
    restore.add_argument('--no-reload', action='store_true')
    restore.add_argument('--backup', type=Path)
    sub.add_parser('status', help='Show required programs and local backup paths')
    args = parser.parse_args()
    paths = locations()
    backups = paths['state'] / 'darwin-theme/kde/backups'
    # Backups made under the former name (golden-gate-theme) stay restorable.
    former = [paths['state'] / 'golden-gate-theme/kde/backups', paths['state'] / 'darwin-osx-theme/kde/backups']

    def all_manifests():
        found = list(backups.glob('*/manifest.json')) + [m for old in former for m in old.glob('*/manifest.json')]
        return sorted(found, key=lambda manifest: manifest.parent.name)   # names start with a timestamp
    if args.command == 'status':
        print(json.dumps({'programs': {p: shutil.which(p) for p in ['plasmashell', 'qdbus6', 'kwriteconfig6', 'plasma-apply-desktoptheme', 'fc-cache']},
                          'backups': [str(p.parent) for p in all_manifests()]}, indent=2))
        return 0
    if args.command == 'restore':
        candidates = [p.parent for p in reversed(all_manifests())
                      if json.loads(p.read_text()).get('status') == 'active']
        directory = args.backup or (candidates[0] if candidates else None)
        if directory is None:
            parser.error('No active backup found')
        # Stop only the desktop shell, never KWin/Wayland or applications. Prevent stale panel writes.
        if not args.no_reload:
            run_checked(['systemctl', '--user', 'stop', 'plasma-plasmashell.service'])
        try:
            restore_backup(directory, paths)
        finally:
            if not args.no_reload:
                start_plasmashell()
                run_checked(['qdbus6', 'org.kde.KWin', '/KWin', 'reconfigure'])
                wait_for_panels(paths)
                if shutil.which('dbus-send'):
                    run_checked(['dbus-send', '--session', '--type=signal', '/KDEPlatformTheme',
                                 'org.kde.KDEPlatformTheme.refreshFonts'])
        return 0
    cfg = configuration()
    if args.command == 'dock':
        script = layout_script(cfg, not args.dock_only, not args.menubar_only, args.dock_mode)
        if args.dry_run:
            print('Native Plasma panel layout (no changes):\n' + script)
            return 0
        if args.no_reload:
            raise ValueError('KDE panels are live objects; use --dry-run or run dock.sh in your Plasma session.')
        run_checked(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell', 'org.freedesktop.DBus.Peer.Ping'])
        wait_for_panels(paths)
        tx = Transaction(paths)
        tx.capture(paths['config'] / 'plasma-org.kde.plasma.desktop-appletsrc')
        tx.capture(paths['config'] / 'plasmashellrc')
        print(f'Backup: {tx.directory}')
        print(run_checked(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script]))
        return 0
    if args.dry_run:
        print('Install Darwin-Dark: decoration, Plasma style, colors, Qt/GTK, Inter fonts, native top menubar and floating dock.\n'
              f'Create timestamped backup under {backups} before changing user-local settings.\n'
              'Preserve wallpaper, existing icon/cursor themes, dock launchers and unrelated settings. No system files touched.\n'
              'Requires Plasma 6, Aurorae, Qt6 Kvantum; optional rounded-corner effect is not installed automatically.')
        return 0
    if not args.no_reload:
        if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', ''):
            parser.error('Run from your KDE Plasma session, or use --no-reload to stage files.')
        for program in ['qdbus6', 'plasma-apply-desktoptheme', 'plasma-apply-colorscheme', 'fc-cache']:
            if not shutil.which(program):
                parser.error(f'Missing dependency: {program}')
        run_checked(['qdbus6', 'org.kde.KWin', '/KWin', 'org.freedesktop.DBus.Peer.Ping'])
        if not args.skip_panels:
            wait_for_panels(paths)
    tx = install_files(args, paths, cfg)
    if not args.no_reload:
        try:
            apply_runtime(tx, cfg)
            reload_desktop(args, cfg, tx)
        except Exception:
            print(f'Live reload failed; backup is available at {tx.directory}', file=sys.stderr)
            raise
    print('Darwin KDE theme installed.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        raise SystemExit(1)
