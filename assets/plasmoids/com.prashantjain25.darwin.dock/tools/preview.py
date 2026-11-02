#!/usr/bin/python3
"""Render the actual TasksModel-backed surface without installing/changing Plasma.

Requires system PyQt6 QtQuick, QtTest, KDE QML modules. Default offscreen;
--wayland also proves the KWin window-task backend, in a temporary preview window.
Native launch test uses an isolated .desktop that only touches a scratch marker.
SPDX-License-Identifier: MIT
"""
import argparse
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--test", action="store_true")
parser.add_argument("--wayland", action="store_true")
parser.add_argument("--nested", action="store_true", help="Isolated headless KWin, no live Plasma changes")
parser.add_argument("--window-test", action="store_true", help=argparse.SUPPRESS)
args = parser.parse_args()
args.output = args.output.resolve()
args.output.mkdir(parents=True, exist_ok=True)
if args.nested:
    import subprocess
    import shlex
    env = os.environ.copy()
    env.update({"KWIN_WAYLAND_NO_PERMISSION_CHECKS": "1", "XDG_CONFIG_HOME": str(args.output / "config"), "LIBGL_ALWAYS_SOFTWARE": "1", "LC_ALL": "C.UTF-8"})
    child = ["/usr/bin/python3", str(Path(__file__).resolve()), "--output", str(args.output), "--wayland", "--window-test"]
    if args.test:
        child.append("--test")
    command = ["dbus-run-session", "--", "kwin_wayland", "--virtual", "--width", "1200", "--height", "800", "--socket", "darwin-test-" + str(os.getpid()), "--no-lockscreen", "--no-global-shortcuts", "--no-kactivities", "--exit-with-session=" + shlex.join(child)]
    # D-Bus-activated services can retain inherited pipe descriptors after KWin
    # exits. A logfile avoids communicate() waiting for unrelated service EOF.
    log_path = args.output / "nested-session.log"
    with log_path.open("w") as log:
        result = subprocess.run(command, env=env, text=True, stdout=log, stderr=subprocess.STDOUT, timeout=70)
    print(log_path.read_text())
    sys.exit(result.returncode)
if args.test:
    # Register ONLY in this process's scratch XDG hierarchy, never the user's.
    os.environ["XDG_DATA_HOME"] = str(args.output / "share")
    os.environ["XDG_CACHE_HOME"] = str(args.output / "cache")
    application_dir = args.output / "share/applications"
    application_dir.mkdir(parents=True, exist_ok=True)
    marker = args.output / "native-launch-confirmed"
    marker.unlink(missing_ok=True)
    desktop = application_dir / "darwin-native-probe.desktop"
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Native launch probe\nIcon=utilities-terminal\nExec=/usr/bin/touch "' + str(marker) + '"\nStartupNotify=false\n')
    import subprocess
    subprocess.run(["kbuildsycoca6", "--noincremental"], check=True, capture_output=True, timeout=20)
os.environ["QT_QPA_PLATFORM"] = "wayland" if args.wayland else "offscreen"
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PyQt6.QtCore import QPoint, QPointF, QUrl, Qt
from PyQt6.QtGui import QGuiApplication, QColor
from PyQt6.QtQml import QQmlEngine
from PyQt6.QtQuick import QQuickView
from PyQt6.QtTest import QTest

app = QGuiApplication(sys.argv)
app.setApplicationName("Darwin Dock Preview")
app.setDesktopFileName("darwin-dock-preview")
view = QQuickView()
view.setTitle("Darwin Dock — isolated native preview")
view.setColor(QColor("#080524"))
errors = []
view.engine().warnings.connect(lambda warnings: errors.extend(w.toString() for w in warnings))
ui = Path(__file__).resolve().parents[1] / "contents/ui"
launchers = ["applications:" + name for name in (
    "org.kde.dolphin.desktop", "google-chrome.desktop", "code.desktop",
    "org.kde.konsole.desktop", "systemsettings.desktop") if (Path("/usr/share/applications") / name).exists()]
if args.test:
    launchers.insert(0, "applications:darwin-native-probe.desktop")
assert launchers, "At least one installed app or --test probe is required"
view.setInitialProperties({"launchers": launchers})
view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
view.setSource(QUrl.fromLocalFile(str(ui / "Dock.qml")))
if view.status() == QQuickView.Status.Error:
    raise RuntimeError("\n".join(e.toString() for e in view.errors()))
root = view.rootObject()
view.resize(max(700, int(root.implicitWidth()) + 64), 144)
view.show()
QTest.qWait(700)


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


def icons():
    return [item for item in walk(root) if item.objectName().startswith(("taskIcon-", "utilityTaskIcon-")) and item.isVisible()]


def capture(name):
    image = view.grabWindow()
    assert not image.isNull(), "QtQuick failed to render a frame"
    assert image.save(str(args.output / name))


backend = root.findChild(__import__("PyQt6.QtCore", fromlist=["QObject"]).QObject, "nativeTasksModel")
assert backend is not None
preserved = backend.property("launcherList") == launchers
assert preserved, (backend.property("launcherList"), launchers)
assert icons(), f"TasksModel did not create native delegates: count={backend.rowCount()}, visual={[(i.objectName(), i.isVisible(), i.width(), i.height()) for i in walk(root)]}"
first = icons()[0]
# Exit the hover region before the idle frame.
QTest.mouseMove(view, QPoint(1, 1))
QTest.qWait(250)
idle = float(first.property("iconSize"))
capture("dock-idle.png")
center = int(first.property("restingCenter"))
QTest.mouseMove(view, QPoint(center, view.height() - 30))
QTest.qWait(350)
hover = float(first.property("iconSize"))
capture("dock-hover.png")
QTest.mouseMove(view, QPoint(1, 1))
# The handler deliberately covers only the visible dock interaction area.
QTest.qWait(350)
restored = float(first.property("iconSize"))

native_launch = False
if args.test:
    # Click the actual rendered delegate and exercise native requestNewInstance.
    probe = next(item for item in icons() if item.property("label") == "Native launch probe")
    print('native probe:', probe.property('index'), [(bytes(n).decode(), backend.data(backend.index(probe.property('index'), 0), r)) for r,n in backend.roleNames().items() if bytes(n).decode() in ('IsLauncher','LauncherUrl','AppName')], flush=True)
    activations = []
    probe.activated.connect(lambda new_instance: activations.append(bool(new_instance)))
    at = probe.mapToItem(root, QPointF(probe.width() / 2, probe.height() - 30))
    QTest.mouseMove(view, QPoint(round(at.x()), round(at.y())))
    QTest.qWait(250)
    at = probe.mapToItem(root, QPointF(probe.width() / 2, probe.height() - 30))
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(at.x()), round(at.y())))
    for _ in range(50):
        if marker.exists():
            native_launch = True
            break
        QTest.qWait(100)
    assert native_launch, f"Native launcher request did not execute isolated .desktop; activations={activations}, point={at}, label={probe.property('label')}, errors={errors}"

# Expose real model data; Wayland mode includes actual KWin window rows.
roles = {bytes(name).decode(): role for role, name in backend.roleNames().items()}
window_requests = False
if args.window_test:
    # Only our isolated preview window is touched, never another application's.
    def own_row():
        return next((r for r in range(backend.rowCount()) if backend.data(backend.index(r, 0), roles["display"]) == view.title() and backend.data(backend.index(r, 0), roles["IsWindow"])), -1)

    def wait_for(predicate):
        for _ in range(40):
            if predicate():
                return True
            QTest.qWait(50)
        return False

    assert wait_for(lambda: own_row() >= 0), "KWin did not expose the preview as a native window task"
    row = own_row()
    backend.requestActivate(backend.index(row, 0))
    assert wait_for(lambda: bool(backend.data(backend.index(own_row(), 0), roles["IsActive"]))), "Preview did not activate"
    root.activateTask(own_row(), False)
    assert wait_for(lambda: bool(backend.data(backend.index(own_row(), 0), roles["IsMinimized"]))), "Active native task click did not minimize"
    root.activateTask(own_row(), False)
    assert wait_for(lambda: bool(backend.data(backend.index(own_row(), 0), roles["IsActive"])) and not bool(backend.data(backend.index(own_row(), 0), roles["IsMinimized"]))), "Minimized native task click did not restore/activate"
    window_requests = True
# Order is judged on what is displayed (left to right), because the dock sorts its own rows.
shown = sorted((item for item in icons() if item.objectName().startswith("taskIcon-")), key=lambda item: item.mapToScene(QPointF(0, 0)).x())
displayed_rows = [int(item.property("modelData")) for item in shown]
pin_positions = [backend.launcherPosition(backend.data(backend.index(row, 0), roles["LauncherUrlWithoutIcon"])) for row in displayed_rows]
pin_positions = [position for position in pin_positions if position >= 0]
assert pin_positions == sorted(pin_positions), f"Supplied pin order was lost: {pin_positions}"
rows = []
for row in range(backend.rowCount()):
    idx = backend.index(row, 0)
    rows.append({name: str(backend.data(idx, roles[name])) for name in ("display", "LauncherUrlWithoutIcon", "IsLauncher", "IsWindow", "IsActive") if name in roles})
report = {
    "platform": app.platformName(),
    "task_count": backend.rowCount(),
    "launchers_preserved": preserved,
    "native_launch_verified": native_launch,
    "native_window_requests_verified": window_requests,
    "pin_order_preserved": pin_positions == sorted(pin_positions),
    "idle_icon_size": idle,
    "hover_icon_size": hover,
    "restored_icon_size": restored,
    "canvas_height": root.property("canvasHeight"),
    "glass_height": root.property("idleHeight"),
    "qml_errors": errors,
    "tasks": rows,
}
(args.output / "report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
assert not errors, errors
assert hover > idle, "Pointer did not magnify the native task delegate"
assert abs(restored - idle) < 0.01, "Pointer exit did not reset magnification"
view.close()
