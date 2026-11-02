"""Safe desktop-entry and D-Bus helpers for the matching KDE components."""
import ast
import json
import re

SPOTLIGHT_SHORTCUTS = [
    ('darwin-spotlight.desktop', 'Spotlight Search', 0x10000000 | 0x20),
    ('darwin-spotlight-files.desktop', 'Spotlight Files', 0x10000000 | 0x02000000 | 0x20),
    ('darwin-spotlight-calc.desktop', 'Spotlight Calculator', 0x10000000 | 0x04000000 | 0x20),
]


# Registered under the former name; released on install so the new launcher can take the same keys.
LEGACY_SERVICES = ['golden-gate-spotlight.desktop', 'golden-gate-spotlight-files.desktop', 'golden-gate-spotlight-calc.desktop',
                   'darwin-osx-spotlight.desktop', 'darwin-osx-spotlight-files.desktop', 'darwin-osx-spotlight-calc.desktop']


def unregister_legacy_shortcuts(run):
    """Best effort: a missing registration is not an error. `run` is subprocess.run-like."""
    for service in LEGACY_SERVICES:
        try:
            run(['gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel', '--object-path', '/kglobalaccel',
                 '--method', 'org.kde.KGlobalAccel.unregister', service, '_launch'], capture_output=True, text=True, timeout=10)
        except (OSError, ValueError):
            pass


def drop_legacy_sections(text):
    """Remove the old [services][golden-gate-spotlight*.desktop] sections from kglobalshortcutsrc text."""
    import re as _re
    pattern = r'^\[services\]\[(?:' + '|'.join(_re.escape(name) for name in LEGACY_SERVICES) + r')\]\n(?:(?!\[).*\n?)*'
    return _re.sub(pattern, '', text, flags=_re.M)


def accel_call(run, method, *arguments):
    return run(['gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel',
                '--object-path', '/kglobalaccel', '--method', 'org.kde.KGlobalAccel.' + method,
                *arguments])


# Fallback when the Qt launcher cannot run (no PyQt6): give KRunner the same key, keeping its own keys.
KRUNNER_SHORTCUTS = [('org.kde.krunner.desktop', 'KRunner', 0x10000000 | 0x20)]


def register_spotlight_shortcuts(tx, run, shortcuts=None):
    tx.capture(tx.paths['config'] / 'kglobalshortcutsrc')
    path = tx.directory / 'runtime.json'
    runtime = json.loads(path.read_text()) if path.exists() else {}
    records = runtime.setdefault('shortcuts', [])
    warnings = []
    for service, label, key in (shortcuts or SPOTLIGHT_SHORTCUTS):
        action = [service, '_launch', label, label]
        previous = shortcut_keys(accel_call(run, 'shortcut', json.dumps(action)))
        available = accel_call(run, 'isGlobalShortcutAvailable', str(key), service)
        if 'true' not in available.lower() and key not in previous:
            warnings.append(f'{label}: shortcut is already assigned; left unchanged')
            continue
        records.append({'id': action, 'keys': previous})
        # Persist before registering: even a partially failed D-Bus sequence is reversible.
        path.write_text(json.dumps(runtime, indent=2) + '\n')
        path.chmod(0o600)
        accel_call(run, 'doRegister', json.dumps(action))
        assigned = shortcut_keys(accel_call(run, 'setShortcut', json.dumps(action), json.dumps(list(dict.fromkeys(previous + [key]))), '6'))
        if key not in assigned:
            raise RuntimeError(f'{label}: KDE did not assign the requested shortcut')
    path.write_text(json.dumps(runtime, indent=2) + '\n')
    path.chmod(0o600)
    return warnings


def restore_spotlight_shortcuts(runtime, run):
    allowed = {item[0] for item in SPOTLIGHT_SHORTCUTS + KRUNNER_SHORTCUTS} | set(LEGACY_SERVICES)   # old backups still restore
    records = runtime.get('shortcuts', [])
    for record in records:
        if (len(record.get('id', [])) != 4 or record['id'][0] not in allowed
                or record['id'][1] != '_launch' or any(type(key) is not int for key in record.get('keys', []))):
            raise ValueError('Unexpected Spotlight shortcut backup')
    for record in reversed(records):
        if record['keys']:
            accel_call(run, 'setShortcut', json.dumps(record['id']), json.dumps(record['keys']), '6')
        else:
            accel_call(run, 'unregister', record['id'][0], record['id'][1])


def shortcut_keys(output):
    cleaned = re.sub(r'@[a-z]+\s+', '', output)
    try:
        keys = ast.literal_eval(cleaned)[0]
    except (SyntaxError, ValueError, TypeError, IndexError) as error:
        raise ValueError('Invalid global-shortcut response') from error
    if not isinstance(keys, list) or any(type(key) is not int for key in keys):
        raise ValueError('Shortcut keys must be integer key codes')
    return keys


def desktop_quote(value):
    if '\n' in value or '\r' in value:
        raise ValueError('A desktop-entry argument cannot contain a newline')
    for old, new in [('\\', '\\\\'), ('"', '\\"'), ('`', '\\`'), ('$', '\\$'), ('%', '%%')]:
        value = value.replace(old, new)
    return '"' + value + '"'
