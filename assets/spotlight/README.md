# Darwin Spotlight (Qt6)

User-local, Wayland-safe launcher matching `assets/launcher/spotlight.rasi`.
No global keyboard grabs, X11 commands, shell evaluation, or background daemon.

## Runtime

Use **system Python** with **PyQt6**, its **QtNetwork** module, **PyGObject/Gio**,
and the Qt Wayland platform plugin. Debian/Ubuntu package names are generally
`python3-pyqt6`, `python3-gi`, `gir1.2-glib-2.0`, and `qt6-wayland`.
A desktop icon theme (for example Breeze) should be installed. Optional
`baloosearch` / `plocate` provide indexed filename search.

```sh
/usr/bin/python3 /absolute/path/to/spotlight/spotlight.py --mode apps
/usr/bin/python3 /absolute/path/to/spotlight/spotlight.py --mode files
/usr/bin/python3 /absolute/path/to/spotlight/spotlight.py --mode calc
/usr/bin/python3 /absolute/path/to/spotlight/spotlight.py --quit
```

Install the **whole directory**, preserving `core.py` and `desktop_launch.py`
beside `spotlight.py`. The parent installer manages copying, shortcuts and
restoration; this component itself writes no desktop configuration.

Render `darwin-spotlight.desktop.in` to the user applications directory as
**`darwin-spotlight.desktop`**. Replace `@SPOTLIGHT_SCRIPT@` with the
**complete desktop-Exec-escaped, double-quoted absolute script path** (the token
is intentionally not quoted in the template). Escape backslash, double quote,
dollar and backtick per desktop Exec syntax; literal percent becomes `%%`.
No shell or `~` expansion is used. The desktop actions expose files/calculator
for separate shortcut entries (suggested Meta+Shift+Space / Meta+Ctrl+Space).
The main application entry is suitable for Meta+Space.

## Wayland placement and lifetime

`QApplication.setDesktopFileName('darwin-spotlight')` establishes the native
app ID. Title is `Darwin Spotlight`; application name is
`darwin-spotlight`. A narrowly scoped KWin rule/script must own absolute
placement: width 25% of the active output, center horizontally, top at 22% of
output height. The widget requests those logical dimensions itself, but a
normal Wayland toplevel cannot force its own coordinates.

The initial launch is a fresh desktop process, allowing Qt/KWin to consume its
Wayland activation token. It uses a normal frameless focusable toplevel, not a
popup. A short initial focus-loss grace avoids map-time dismissal. After actual
activation, normal focus loss dismisses. **Escape, successful Enter activation,
window close, and the next local-socket invocation all exit the process**.
There is no hidden-server reactivation path or unverifiable token forwarding.
Invoking another mode while this launcher is visible dismisses it as well;
invoke again to open that mode fresh.

The per-user Qt local socket is `darwin-spotlight.sock` in
`XDG_RUNTIME_DIR`; startup is serialized with a Qt lock file. Socket messages
only dismiss; they cannot supply commands to execute.

## Interaction and safety

- Type to rank real installed XDG desktop applications, with user overrides,
  visibility filters, keywords and current-desktop constraints.
- Up/Down select (wrap); Enter starts the selected desktop file through Gio.
  Exec field codes, quoting, Terminal and working directory are Gio's concern.
- `--mode calc`, or an `=` prefix in app mode, evaluates only bounded numeric
  AST arithmetic (`+ - * / // % **`, parentheses, unary signs; `^` means power).
  Enter copies the result to the clipboard and exits. No Python `eval`.
- `--mode files` searches names, never file contents. Empty input exposes no
  files. Debounced jobs run off the GUI thread; each query is capped at seven
  results and about 0.8 seconds. Baloo and plocate have individual subprocess
  timeouts/result caps. If indexes miss, fallback examines at most 1500 entries,
  two levels deep in Desktop/Documents/Downloads, not the whole home tree.
  Indexed results are restricted to the home directory. No network search.
- Stale worker results are rejected; editing immediately invalidates selection.
  Files are opened with Qt desktop services using a local-file URL.

## Tests and rendering evidence

From the repository root:

```sh
python3 -m unittest discover -s tests -p test_spotlight_component.py -v
QT_QPA_PLATFORM=offscreen /usr/bin/python3 -m unittest discover -s tests -p test_spotlight_component.py -v
```

The first command supports stdlib-only Python (GUI/Gio tests skip if missing).
The system-Python command exercises real installed application search, a real
Gio desktop-file launch into a temporary argv recorder, safe calculation,
bounded real-file search, keyboard interaction, local socket dismissal and
fresh process restart. Qt critical/fatal messages fail the render test.

The screenshot is a widget grab of **real installed applications**, never
invented mock rows. It defaults to `$TMPDIR/darwin-spotlight.png` (Python's
temporary directory); set `SPOTLIGHT_SCREENSHOT` to override. No screenshot or
personal search results are stored in this package. Offscreen tests do **not**
prove KWin focus/placement; real desktop shortcut verification remains required.
