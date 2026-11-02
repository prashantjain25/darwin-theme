#!/usr/bin/python3
"""Darwin Spotlight: native Qt6 launcher, no X11 grabs or shell Exec parsing.
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import argparse
import configparser
from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

from PyQt6.QtCore import (QEvent, QLockFile, QObject, QPoint, QRect, QRectF, QRunnable,
                          QSize, QStandardPaths, Qt, QThreadPool, QTimer, QUrl,
                          pyqtSignal)
from PyQt6.QtGui import QColor, QCursor, QDesktopServices, QFont, QIcon, QPainter, QPen
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QVBoxLayout, QWidget)

from core import (calculate, evaluate_expression, find_files, load_applications_cached, looks_like_conversion,
                  looks_like_math, search_applications)
from desktop_launch import launch_application


def configure_icons():
    """PyQt without the KDE platform plugin still needs normal XDG icon lookup."""
    data = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.GenericDataLocation)
    paths = list(dict.fromkeys([*QIcon.themeSearchPaths(), str(Path.home() / ".icons"),
                               *(str(Path(root) / "icons") for root in data)]))
    QIcon.setThemeSearchPaths(paths)
    QIcon.setFallbackSearchPaths([*QIcon.fallbackSearchPaths(), "/usr/share/pixmaps"])
    QIcon.setFallbackThemeName("breeze-dark")
    if not QIcon.themeName():
        config = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            config.read(Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "kdeglobals")
            theme = config.get("Icons", "Theme", fallback="breeze-dark")
        except (OSError, configparser.Error):
            theme = "breeze-dark"
        QIcon.setThemeName(theme)


@dataclass(frozen=True)
class Result:
    kind: str
    label: str
    target: str
    icon: str


class TaskSignals(QObject):
    completed = pyqtSignal(str, int, object)


class Task(QRunnable):
    def __init__(self, kind, serial, work):
        super().__init__()
        self.kind, self.serial, self.work = kind, serial, work
        self.signals = TaskSignals()

    def run(self):
        try:
            value = self.work()
        except Exception:
            value = None  # Do not expose personal paths or backend output in the UI/log.
        try:
            self.signals.completed.emit(self.kind, self.serial, value)
        except RuntimeError:
            pass   # the launcher closed while this lookup was running; nobody is waiting for the answer


class SearchIcon(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        painter.setPen(QPen(QColor(245, 245, 245, 160), max(1.5, side / 16)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPoint(round(side * .43), round(side * .43)), round(side * .23), round(side * .23))
        painter.drawLine(QPoint(round(side * .60), round(side * .60)), QPoint(round(side * .80), round(side * .80)))


class Spotlight(QWidget):
    """Visible-only launcher. dismissed makes main exit, never a hidden daemon.

    KWin owns absolute placement on Wayland; the desktop ID/title is stable for
    a scoped compositor rule. move() also provides the correct X11/offscreen hint.
    """
    dismissed = pyqtSignal()

    def __init__(self, screen_geometry: QRect | None = None):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Darwin Spotlight")
        self.setObjectName("darwin-spotlight")
        configure_icons()
        self.geometry_override = screen_geometry
        self.mode = "apps"
        self.apps = []
        self._app_rows, self._calc_rows, self._file_rows = [], [], []
        self._loaded = False
        self._serial = 0
        self._tasks = {}
        self._cancel = threading.Event()
        self._shown_at = 0.0
        self._seen_activation = False
        self._stopping = False
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header_layout = QHBoxLayout(self.header)
        self.search_icon = SearchIcon()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Spotlight Search")
        self.input.setMaxLength(256)
        self.input.setFrame(False)
        self.input.setClearButtonEnabled(False)
        self.input.setAccessibleName("Spotlight Search")
        self.input.installEventFilter(self)
        self.header_layout.addWidget(self.search_icon)
        self.header_layout.addWidget(self.input, 1)
        outer.addWidget(self.header)
        self.results = QListWidget()
        self.results.setAccessibleName("Spotlight results")
        self.results.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.results.setIconSize(QSize(30, 30))
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results.setMouseTracking(True)
        self.results.setSpacing(1)
        self.results.itemEntered.connect(lambda item: self.results.setCurrentItem(item))
        self.results.itemClicked.connect(lambda item: self.activate_result())
        outer.addWidget(self.results)
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setContentsMargins(18, 9, 18, 12)
        outer.addWidget(self.status)
        self.setStyleSheet("""
            QWidget { color: #f5f5f5; background: transparent; }
            QFrame#header { border: none; border-bottom: 1px solid rgba(255,255,255,26); }
            QLineEdit { border: none; padding: 0; selection-background-color: #0091ff;
                        placeholder-text-color: rgba(255,255,255,115); }
            QListWidget { border: none; padding: 6px; outline: none; }
            QListWidget::item { border: none; border-radius: 8px; padding: 7px 12px; }
            QListWidget::item:selected { background: #0091ff; color: white; }
            QLabel#status { color: rgba(255,255,255,115); font-size: 12px; }
        """)
        self._async_job = None
        self.async_timer = QTimer(self)
        self.async_timer.setSingleShot(True)
        self.async_timer.setInterval(180)
        self.async_timer.timeout.connect(self._start_async)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(100)
        self.debounce.timeout.connect(self.refresh)
        self.input.textChanged.connect(self.query_changed)
        self._start_task("apps", 0, load_applications_cached)

    def _start_task(self, kind, serial, work):
        task = Task(kind, serial, work)
        task.signals.completed.connect(self._completed)
        self._tasks[(kind, serial)] = task
        self.pool.start(task)

    def _completed(self, kind, serial, value):
        self._tasks.pop((kind, serial), None)
        if self._stopping:
            return
        if kind == "apps":
            self.apps, self._loaded = value or [], True
            if self.mode == "apps":
                self.refresh()
        elif serial != self._serial:
            return   # a newer query is already on screen
        elif kind == "files":
            rows = [Result("file", path.name, str(path), "folder" if path.is_dir() else "text-x-generic") for path in (value or [])]
            if self.mode == "files":
                self.set_results(rows, "No matching files (index or Desktop/Documents/Downloads)")
            elif self.mode == "apps":
                self._file_rows = rows[:3]
                self._compose(keep=True)
        elif kind == "calc":
            rows = [Result("calc", value + "   (Enter to copy)", value, "accessories-calculator")] if value else []
            if self.mode == "calc":
                self.set_results(rows, "Not understood. Try 12*(3+4) or 100 USD to EUR")
            elif self.mode == "apps":
                self._calc_rows = rows
                self._compose(keep=True)

    def _start_async(self):
        job, self._async_job = self._async_job, None
        if not job or self.mode != "apps" or job[0] != self._serial:
            return
        serial, query, expression, may_convert, cancel = job
        if may_convert and (looks_like_conversion(query) or query.startswith("=")):
            self._start_task("calc", serial, lambda: evaluate_expression(expression))
        if len(query) >= 2 and not query.startswith("="):
            self._start_task("files", serial, lambda: find_files(query, cancelled=cancel, limit=3))

    def _compose(self, keep=False):
        """One list, like macOS Spotlight: calculator/currency answer, applications, then matching files."""
        budget = 7 - len(self._calc_rows) - len(self._file_rows)
        rows = self._calc_rows + self._app_rows[:max(1, budget)] + self._file_rows
        self.set_results(rows[:7], "No matching applications" if self._loaded else "Loading applications…", keep=keep)

    def screen_geometry(self):
        if self.geometry_override is not None:
            return self.geometry_override
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        return screen.geometry()

    def apply_geometry(self):
        rect = self.screen_geometry()
        width = min(rect.width() - 16, max(280, round(rect.width() * .25)))
        self.radius = max(6, round(6 / 982 * rect.width()))
        self.setFixedWidth(width)
        icon = max(18, round(16 / 982 * rect.width()))
        self.search_icon.setFixedSize(icon, icon)
        self.header_layout.setContentsMargins(round(8 / 1512 * rect.width()),
                                               round(4 / 982 * rect.width()),
                                               round(4 / 1512 * rect.width()),
                                               round(4 / 982 * rect.width()))
        self.header_layout.setSpacing(max(3, round(2 / 1512 * rect.width())))
        font = QFont("Inter")
        font.setPointSize(max(10, round(13 * rect.width() / 1512 * 72 / 96)))
        self.input.setFont(font)
        # rofi applies one font to the whole window, so result rows use the search-field size.
        self.results.setFont(font)
        self.move(rect.x() + round((rect.width() - width) / 2), rect.y() + round(rect.height() * .22))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 46), 1))
        painter.setBrush(QColor(40, 40, 44, 245))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), self.radius, self.radius)

    def show_launcher(self, mode="apps"):
        self.mode = mode
        self._shown_at = time.monotonic()
        self._seen_activation = False
        self._dismissing = False
        self.apply_geometry()
        self.input.blockSignals(True)
        self.input.clear()
        self.input.blockSignals(False)
        self.input.setPlaceholderText({"apps": "Spotlight Search", "files": "Search Files", "calc": "Calculate"}[mode])
        self.refresh()
        self.show()
        # Use a normal focusable toplevel, not Qt.Popup (which can instantly
        # dismiss on Wayland map). Fresh desktop launches consume their own token.
        QTimer.singleShot(0, self._request_focus)

    def _request_focus(self):
        if not self.isVisible():
            return
        if QApplication.platformName() != "offscreen":
            self.activateWindow()
            if self.windowHandle():
                self.windowHandle().requestActivate()
        self.input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def query_changed(self):
        self._cancel.set()
        self._serial += 1
        if self.mode == "files":
            self.set_results([], "Searching…" if self.input.text().strip() else "Type a filename to search")
            self.debounce.start()
        else:
            # Local app ranking/arithmetic is cheap. Update synchronously so
            # a fast Enter can never activate a stale pre-edit selection.
            self.refresh()

    def refresh(self):
        if self._stopping:
            return
        query = self.input.text().strip()
        self._cancel.set()
        self._cancel = threading.Event()
        self._serial += 1
        cancel = self._cancel
        if self.mode == "calc":
            local = calculate(query) if query else None
            if local is not None:
                self.set_results([Result("calc", local + "   (Enter to copy)", local, "accessories-calculator")], "")
            elif query:
                self.set_results([], "Calculating…")
                self._start_task("calc", self._serial, lambda: evaluate_expression(query))
            else:
                self.set_results([], "Type a calculation, e.g. 12*(3+4) or 100 USD to EUR")
        elif self.mode == "files":
            self.set_results([], "Searching…" if query else "Type a filename to search")
            if query:
                self._start_task("files", self._serial, lambda: find_files(query, cancelled=cancel))
        else:
            self._app_rows = [Result("app", app.name, app.desktop_file, app.icon) for app in search_applications(self.apps, query)]
            self._calc_rows, self._file_rows = [], []
            expression = query.removeprefix("=").strip()
            local = calculate(expression) if (query.startswith("=") or looks_like_math(query)) else None
            if local is not None:
                self._calc_rows = [Result("calc", local + "   (Enter to copy)", local, "accessories-calculator")]
            # Slow lookups (network rates, file index) start only once typing pauses.
            self._async_job = (self._serial, query, expression, local is None, cancel)
            self.async_timer.start()
            self._compose()

    def set_results(self, rows, empty_message, keep=False):
        previous = self.results.currentRow() if keep else 0
        self.results.clear()
        for result in rows[:7]:
            icon = QIcon(result.icon) if Path(result.icon).is_absolute() else QIcon.fromTheme(result.icon)
            if icon.isNull():
                icon = QIcon.fromTheme("application-x-executable")
            item = QListWidgetItem(icon, result.label)
            item.setData(Qt.ItemDataRole.UserRole, result)
            item.setSizeHint(QSize(0, 44))
            self.results.addItem(item)
        self.results.setVisible(bool(rows))
        self.results.setFixedHeight(len(rows[:7]) * 46 + 12 if rows else 0)
        self.status.setText(empty_message if not rows else "")
        self.status.setVisible(not rows)
        if rows:
            self.results.setCurrentRow(min(max(previous, 0), len(rows[:7]) - 1))
        self.adjustSize()

    def activate_result(self):
        item = self.results.currentItem()
        if item is None:
            return
        result = item.data(Qt.ItemDataRole.UserRole)
        try:
            if result.kind == "app":
                launch_application(result.target)
            elif result.kind == "file":
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(result.target)):
                    raise RuntimeError("Cannot open file")
            else:
                QApplication.clipboard().setText(result.target)
        except Exception:
            self.status.setText("Could not open selection")
            self.status.show()
            self.adjustSize()
            return
        self.dismiss()

    def eventFilter(self, watched, event):
        if watched is self.input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.dismiss()
                return True
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                count = self.results.count()
                if count:
                    self.results.setCurrentRow((self.results.currentRow() + (1 if key == Qt.Key.Key_Down else -1)) % count)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.activate_result()
                return True
        return super().eventFilter(watched, event)

    def event(self, event):
        if event.type() == QEvent.Type.WindowActivate:
            self._seen_activation = True
        elif event.type() == QEvent.Type.WindowDeactivate:
            # Ignore initial compositor focus churn. Only a toplevel which
            # actually had focus may dismiss on a subsequent focus loss.
            if self._seen_activation and time.monotonic() - self._shown_at > .4:
                self.dismiss()
        return super().event(event)

    def dismiss(self):
        # hide() sends a deactivate event that asks to dismiss again; ignore that second call.
        if getattr(self, "_dismissing", False):
            return
        self._dismissing = True
        self._cancel.set()
        self.hide()
        self.dismissed.emit()

    def closeEvent(self, event):
        self.dismiss()
        event.accept()

    def shutdown(self):
        self._stopping = True
        self._cancel.set()
        self.debounce.stop()
        self.async_timer.stop()
        self.pool.clear()
        self.pool.waitForDone(1500)
        self.hide()


class InstanceBroker(QObject):
    """User-only local socket; a second launch dismisses the visible instance.

    No hidden server/reactivation path: Escape, genuine focus loss, activation
    and socket toggle all exit main, so the next launch gets a fresh Wayland token.
    """
    message = pyqtSignal(dict)

    def __init__(self, name=None):
        super().__init__()
        runtime = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.RuntimeLocation)
        self.name = name or str(Path(runtime) / "darwin-spotlight.sock")
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self.clients = {}

    def claim(self, mode="apps", quit_only=False):
        lock = QLockFile(self.name + ".lock")
        if not lock.tryLock(1500):
            raise RuntimeError("Spotlight instance is busy")
        try:
            client = QLocalSocket()
            client.connectToServer(self.name)
            if client.waitForConnected(300):
                client.write(json.dumps({"mode": mode, "action": "dismiss"}).encode() + b"\n")
                client.waitForBytesWritten(300)
                client.disconnectFromServer()
                return False
            if quit_only:
                return False
            QLocalServer.removeServer(self.name)
            if not self.server.listen(self.name):
                raise RuntimeError("Cannot create Spotlight local socket")
            return True
        finally:
            lock.unlock()

    def _accept(self):
        while self.server.hasPendingConnections():
            client = self.server.nextPendingConnection()
            self.clients[client] = bytearray()
            client.readyRead.connect(lambda c=client: self._read(c))
            client.disconnected.connect(lambda c=client: self._drop(c))
            QTimer.singleShot(1000, lambda c=client: c.disconnectFromServer() if c in self.clients else None)
            self._read(client)
            if client in self.clients and client.bytesAvailable() == 0:
                client.waitForReadyRead(150)   # the sender may still be writing
                self._read(client)

    def _read(self, client):
        buffer = self.clients.get(client)
        if buffer is None:
            return
        buffer.extend(bytes(client.readAll()))
        if len(buffer) > 1024:
            client.disconnectFromServer()
        elif b"\n" in buffer:
            try:
                message = json.loads(bytes(buffer).split(b"\n", 1)[0])
                if message.get("mode") in ("apps", "files", "calc") and message.get("action") == "dismiss":
                    self.message.emit(message)
            except (ValueError, AttributeError):
                pass
            client.disconnectFromServer()

    def _drop(self, client):
        if client.isOpen():
            self._read(client)   # data and the disconnect can arrive together; read the message before forgetting the client
        self.clients.pop(client, None)
        client.deleteLater()

    def close(self):
        self.server.close()
        for client in list(self.clients):
            client.abort()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("apps", "files", "calc"), default="apps")
    parser.add_argument("--quit", action="store_true", help="Dismiss an existing instance without opening one")
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("darwin-spotlight")
    app.setDesktopFileName("darwin-spotlight")
    app.setQuitOnLastWindowClosed(False)
    broker = InstanceBroker()
    if not broker.claim(args.mode, quit_only=args.quit):
        return 0
    window = Spotlight()
    window.dismissed.connect(app.quit)
    broker.message.connect(lambda message: window.dismiss())
    app.aboutToQuit.connect(window.shutdown)
    app.aboutToQuit.connect(broker.close)
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    # Return to Python periodically so POSIX signals are delivered while idle.
    pulse = QTimer()
    pulse.timeout.connect(lambda: None)
    pulse.start(200)
    window.show_launcher(args.mode)
    return app.exec()


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    # Cleanup (socket, lock, workers) already ran in aboutToQuit. Leave now instead of waiting on an
    # application scan that is still running in a pool thread.
    os._exit(code or 0)
