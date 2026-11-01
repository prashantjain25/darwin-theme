#!/usr/bin/env python3
"""Install the window switcher and reversibly release Openbox's Alt+Tab bindings."""
import base64
from pathlib import Path
import re
import shlex
from theme import load, resolve


def patch_rc(path, enabled):
    text = Path(path).read_text()
    # Keep the original bindings (including custom actions) for style=list.
    text = re.sub(r'<!-- golden-gate-alttab:([A-Za-z0-9+/=]+) -->',
                  lambda m: base64.b64decode(m[1]).decode(), text)
    if enabled:
        def disable(match):
            block = match[0]
            if block.startswith('<!--'):
                return block
            key = re.search(r'\bkey=[\"\']([^\"\']+)', block)
            if key and set(key[1].split('-')) in ({'A', 'Tab'}, {'A', 'S', 'Tab'}, {'A', 'Escape'}):
                return '<!-- golden-gate-alttab:' + base64.b64encode(block.encode()).decode() + ' -->'
            return block
        text = re.sub(r'<!--.*?-->|<keybind\b[^>]*>.*?</keybind>', disable, text, flags=re.S)
    Path(path).write_text(text)


def install():
    cfg = load()
    env = resolve(cfg)
    home = Path.home()
    launcher = home / '.local/bin/golden-gate-switcher'
    desktop = home / '.config/autostart/golden-gate-switcher.desktop'
    enabled = cfg['switcher']['style'] == 'icons'
    for name in ('rc.xml', 'lxqt-rc.xml'):
        rc = home / '.config/openbox' / name
        if rc.exists():
            patch_rc(rc, enabled)
    if not enabled:
        launcher.unlink(missing_ok=True)
        desktop.unlink(missing_ok=True)
        (home / '.local/lib/golden-gate/window_switcher.py').unlink(missing_ok=True)
        return
    module = home / '.local/lib/golden-gate/window_switcher.py'
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text(Path(__file__).with_name('window_switcher.py').read_text())
    args = ['/usr/bin/python3', str(module), '--opacity', str(env['SWITCHER_OPACITY']),
            '--background', cfg['switcher'].get('background', '#dedede'),
            '--foreground', cfg['switcher'].get('foreground', '#1a1a1a'),
            '--font', cfg['fonts']['ui'], '--radius', str(env['SWITCHER_R'])]
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text('#!/bin/sh\nmkdir -p "$HOME/.cache"\n'
                        'echo "$$" > "$HOME/.cache/golden-gate-switcher.pid"\n'
                        'exec ' + shlex.join(args) + '\n')
    launcher.chmod(0o755)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    exe = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Golden Gate Window Switcher\n'
                       'Exec="' + exe + '"\nTryExec=/usr/bin/python3\nOnlyShowIn=LXQt;\n'
                       'X-LXQt-Need-Tray=false\nX-LXQt-X11-Only=true\n')


if __name__ == '__main__':
    install()
