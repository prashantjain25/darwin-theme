#!/usr/bin/env python3
"""Select the running desktop, never an arbitrary installed desktop package."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def detect(env, explicit=None):
    if explicit and explicit != 'auto':
        if explicit not in ('kde', 'lxqt'):
            raise ValueError('--desktop must be auto, kde or lxqt')
        return explicit
    current = env.get('XDG_CURRENT_DESKTOP', '')
    text = current or env.get('XDG_SESSION_DESKTOP', '') or env.get('DESKTOP_SESSION', '')
    tokens = text.lower().replace(';', ':').split(':')
    matches = set()
    if any(t in ('kde', 'plasma', 'plasmawayland', 'plasmax11') for t in tokens):
        matches.add('kde')
    if any(t in ('lxqt', 'lubuntu') for t in tokens):
        matches.add('lxqt')
    if len(matches) != 1:
        raise ValueError(f'Cannot safely select KDE/LXQt from desktop {text!r}; pass --desktop kde or --desktop lxqt')
    return matches.pop()


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('install', 'dock', 'restore'):
        raise ValueError('Expected install, dock or restore')
    action, args = sys.argv[1], list(sys.argv[2:])
    explicit = os.environ.get('GG_DESKTOP', 'auto')
    forwarded = []
    while args:
        arg = args.pop(0)
        if arg == '--desktop':
            if not args:
                raise ValueError('--desktop needs auto, kde or lxqt')
            explicit = args.pop(0).lower()
        elif arg.startswith('--desktop='):
            explicit = arg.split('=', 1)[1].lower()
        else:
            forwarded.append(arg)
    desktop = detect(os.environ, explicit)
    if desktop == 'lxqt':
        os.execvp('bash', ['bash', str(ROOT / f'{action}-lxqt.sh'), *forwarded])
    # KDE has no dependency on the legacy X11 compositor or launcher.
    mapped = ['--no-reload' if arg == '--no-restart' else arg for arg in forwarded if arg not in ('-y', '--yes')]
    os.execv(sys.executable, [sys.executable, str(ROOT / 'lib/kde.py'), action, *mapped])


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        print(f'Error: {error}', file=sys.stderr)
        raise SystemExit(2)
