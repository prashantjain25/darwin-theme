#!/usr/bin/python3
"""X11 Alt+Tab overlay: native alpha background, opaque icons and selected label."""
import argparse
import array
import ctypes as C
import ctypes.util
import os
import signal
import sys
import time
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

U = C.c_ulong
P = C.c_void_p


class KeyEvent(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', U), ('send_event', C.c_int),
                ('display', P), ('window', U), ('root', U), ('subwindow', U),
                ('time', U), ('x', C.c_int), ('y', C.c_int), ('x_root', C.c_int),
                ('y_root', C.c_int), ('state', C.c_uint), ('keycode', C.c_uint),
                ('same_screen', C.c_int)]


class ClientEvent(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', U), ('send_event', C.c_int),
                ('display', P), ('window', U), ('message_type', U),
                ('format', C.c_int), ('data', C.c_long * 5)]


class Event(C.Union):
    _fields_ = [('type', C.c_int), ('key', KeyEvent), ('client', ClientEvent),
                ('pad', C.c_long * 24)]


class X11:
    def __init__(self):
        self.x = C.CDLL(ctypes.util.find_library('X11'))
        signatures = {
            'XOpenDisplay': ([C.c_char_p], P),
            'XDefaultRootWindow': ([P], U),
            'XInternAtom': ([P, C.c_char_p, C.c_int], U),
            'XGetWindowProperty': ([P, U, U, C.c_long, C.c_long, C.c_int, U,
                                   C.POINTER(U), C.POINTER(C.c_int), C.POINTER(U),
                                   C.POINTER(U), C.POINTER(P)], C.c_int),
            'XFree': ([P], C.c_int),
            'XKeysymToKeycode': ([P, U], C.c_ubyte),
            'XGrabKey': ([P, C.c_int, C.c_uint, U, C.c_int, C.c_int, C.c_int], C.c_int),
            'XUngrabKey': ([P, C.c_int, C.c_uint, U], C.c_int),
            'XGrabKeyboard': ([P, U, C.c_int, C.c_int, C.c_int, U], C.c_int),
            'XUngrabKeyboard': ([P, U], C.c_int),
            'XPending': ([P], C.c_int),
            'XNextEvent': ([P, C.POINTER(Event)], C.c_int),
            'XSendEvent': ([P, U, C.c_int, C.c_long, C.POINTER(Event)], C.c_int),
            'XFlush': ([P], C.c_int),
            'XQueryKeymap': ([P, C.c_char_p], C.c_int),
            'XCloseDisplay': ([P], C.c_int),
        }
        for name, (args, result) in signatures.items():
            getattr(self.x, name).argtypes = args
            getattr(self.x, name).restype = result
        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError('Cannot connect to the X11 desktop')
        self.root = self.x.XDefaultRootWindow(self.display)
        self.atoms = {}
        # A window can close while its properties are being read.
        self.errors = []
        self.error_handler = C.CFUNCTYPE(C.c_int, P, P)(lambda d, e: self.errors.append(1) or 0)
        self.x.XSetErrorHandler.argtypes = [P]
        self.x.XSetErrorHandler(self.error_handler)

    def atom(self, name):
        if name not in self.atoms:
            self.atoms[name] = self.x.XInternAtom(self.display, name.encode(), False)
        return self.atoms[name]

    def prop(self, window, name):
        actual, fmt, count, remaining, data = U(), C.c_int(), U(), U(), P()
        status = self.x.XGetWindowProperty(self.display, window, self.atom(name),
                                           0, 1048576, False, 0, C.byref(actual),
                                           C.byref(fmt), C.byref(count), C.byref(remaining), C.byref(data))
        if status or not data:
            return []
        try:
            if fmt.value == 32:
                return list(C.cast(data, C.POINTER(U * count.value)).contents)
            if fmt.value == 8:
                return C.string_at(data, count.value)
            return []
        finally:
            self.x.XFree(data)

    def key(self, symbol):
        return self.x.XKeysymToKeycode(self.display, symbol)

    def active(self):
        ids = self.prop(self.root, '_NET_ACTIVE_WINDOW')
        return ids[0] if ids else 0

    def activate(self, window):
        desktop = self.prop(window, '_NET_WM_DESKTOP')
        if desktop and desktop[0] != 0xffffffff:
            self.send(self.root, '_NET_CURRENT_DESKTOP', [desktop[0], 0])
        self.send(window, '_NET_ACTIVE_WINDOW', [2, 0, self.active()])

    def send(self, window, message, values):
        event = Event()
        event.client.type = 33
        event.client.window = window
        event.client.message_type = self.atom(message)
        event.client.format = 32
        for index, value in enumerate(values):
            event.client.data[index] = value
        self.x.XSendEvent(self.display, self.root, False, (1 << 20) | (1 << 19), C.byref(event))
        self.x.XFlush(self.display)

    def icon(self, window, app):
        values = self.prop(window, '_NET_WM_ICON')
        choices, index = [], 0
        while index + 2 <= len(values):
            width, height = values[index:index + 2]
            end = index + 2 + width * height
            if not width or not height or end > len(values):
                break
            if width <= 512 and height <= 512:
                choices.append((abs(max(width, height) - 128), width, height, index + 2, end))
            index = end
        if choices:
            _, width, height, start, end = min(choices)
            pixels = array.array('I', [p & 0xffffffff for p in values[start:end]])
            img = QtGui.QImage(pixels.tobytes(), width, height, width * 4,
                               QtGui.QImage.Format.Format_ARGB32).copy()
            return QtGui.QPixmap.fromImage(img)
        icon = QtGui.QIcon.fromTheme(app.lower())
        if icon.isNull():
            icon = QtGui.QIcon.fromTheme('application-x-executable')
        return icon.pixmap(88, 88)

    def windows(self, history):
        stacking = self.prop(self.root, '_NET_CLIENT_LIST_STACKING')
        if not stacking:
            stacking = self.prop(self.root, '_NET_CLIENT_LIST')
        excluded = {self.atom('_NET_WM_WINDOW_TYPE_DOCK'), self.atom('_NET_WM_WINDOW_TYPE_DESKTOP')}
        windows = []
        for wid in reversed(stacking):
            if excluded.intersection(self.prop(wid, '_NET_WM_WINDOW_TYPE')):
                continue
            if self.atom('_NET_WM_STATE_SKIP_TASKBAR') in self.prop(wid, '_NET_WM_STATE'):
                continue
            classes = self.prop(wid, 'WM_CLASS')
            names = classes.decode(errors='replace').strip('\0').split('\0') if classes else []
            app = names[-1] if names else 'Application'
            if 'GoldenGateSwitcher' in names:
                continue
            title = self.prop(wid, '_NET_WM_NAME') or self.prop(wid, 'WM_NAME')
            title = title.decode(errors='replace').strip('\0') if isinstance(title, bytes) else app
            # The selected label names the app; window identity remains separate.
            label = {'Google-chrome': 'Google Chrome', 'google-chrome': 'Google Chrome',
                     'pcmanfm-qt': 'Files', 'Pcmanfm-qt': 'Files', 'qterminal': 'Terminal',
                     'QTerminal': 'Terminal', 'jetbrains-idea': 'IntelliJ IDEA'}.get(app, app)
            windows.append({'id': wid, 'label': label, 'title': title, 'icon': self.icon(wid, app)})
        active = self.active()
        rank = {wid: i for i, wid in enumerate(history)}
        windows.sort(key=lambda w: (-1 if w['id'] == active else rank.get(w['id'], len(rank))))
        return windows


class Switcher(QtWidgets.QWidget):
    def __init__(self, args):
        super().__init__(None, QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint |
                         QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.X11BypassWindowManagerHint |
                         QtCore.Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle('Golden Gate Window Switcher')
        self.setMouseTracking(True)
        self.args, self.x11 = args, X11()
        self.items, self.selected = [], 0
        self.previous = self.x11.active()
        self.history = [self.previous] if self.previous else []
        self.alt_codes = [self.x11.key(0xffe9), self.x11.key(0xffea)]
        self.tab, self.escape = self.x11.key(0xff09), self.x11.key(0xff1b)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(12)
        for mod in (8, 8 | 1):
            for locks in (0, 2, 16, 18):
                self.x11.x.XGrabKey(self.x11.display, self.tab, mod | locks,
                                    self.x11.root, False, 1, 1)
        self.x11.x.XFlush(self.x11.display)
        self.icon_size, self.tile, self.padding = 88, 108, 20
        self.opened_at = 0

    def begin(self, backward):
        self.items = self.x11.windows(self.history)
        if not self.items:
            self.x11.x.XUngrabKeyboard(self.x11.display, 0)
            return
        self.selected = (len(self.items) - 1 if backward else 1) % len(self.items)
        screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos()) or QtGui.QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.tile = min(108, max(44, (area.width() - 80) // len(self.items)))
        self.icon_size = min(88, self.tile - 20)
        self.resize(self.tile * len(self.items) + 2 * self.padding, 148)
        self.move(area.center().x() - self.width() // 2, area.center().y() - self.height() // 2)
        self.opened_at = time.monotonic()
        self.show()
        self.raise_()
        self.x11.x.XGrabKeyboard(self.x11.display, self.x11.root, False, 1, 1, 0)
        self.update()

    def finish(self, accept):
        self.hide()
        self.x11.x.XUngrabKeyboard(self.x11.display, 0)
        self.x11.x.XFlush(self.x11.display)
        if accept and self.items:
            wid = self.items[self.selected]['id']
            self.history = [wid] + [w for w in self.history if w != wid]
            self.x11.activate(wid)

    def poll(self):
        active = self.x11.active()
        if not self.isVisible() and active and active != self.previous:
            self.history = [active] + [w for w in self.history if w != active]
            self.previous = active
        while self.x11.x.XPending(self.x11.display):
            event = Event()
            self.x11.x.XNextEvent(self.x11.display, C.byref(event))
            if event.type == 2 and event.key.keycode == self.tab:
                backward = bool(event.key.state & 1)
                if self.isVisible():
                    self.selected = (self.selected + (-1 if backward else 1)) % len(self.items)
                    self.update()
                else:
                    self.begin(backward)
            elif event.type == 2 and event.key.keycode == self.escape and self.isVisible():
                self.finish(False)
            elif event.type == 3 and event.key.keycode in self.alt_codes and self.isVisible():
                self.finish(True)
        # Querying modifier state also handles an Alt release that arrives during
        # the passive-to-active grab handover or during window creation.
        if self.isVisible() and time.monotonic() - self.opened_at > .08:
            keys = C.create_string_buffer(32)
            self.x11.x.XQueryKeymap(self.x11.display, keys)
            if not any(keys.raw[k // 8] & (1 << (k % 8)) for k in self.alt_codes):
                self.finish(True)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        bg = QtGui.QColor(self.args.background)
        bg.setAlphaF(self.args.opacity / 100)
        p.setBrush(bg)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawRoundedRect(QtCore.QRectF(self.rect()), self.args.radius, self.args.radius)
        for i, item in enumerate(self.items):
            x = self.padding + i * self.tile
            if i == self.selected:
                p.setBrush(QtGui.QColor(0, 0, 0, 40))
                p.drawRoundedRect(QtCore.QRectF(x, 20, self.tile, 108), 7, 7)
            icon = item['icon'].scaled(self.icon_size, self.icon_size,
                                       QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                       QtCore.Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(x + (self.tile - icon.width()) // 2, 30 + (88 - icon.height()) // 2, icon)
        if self.items:
            p.setPen(QtGui.QColor(self.args.foreground))
            p.setFont(QtGui.QFont(self.args.font, 10))
            label = p.fontMetrics().elidedText(self.items[self.selected]['label'],
                                               QtCore.Qt.TextElideMode.ElideRight, self.tile + 20)
            p.drawText(QtCore.QRect(self.padding + self.selected * self.tile - 10, 129, self.tile + 20, 18),
                       QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter, label)

    def mouseMoveEvent(self, event):
        selected = int((event.position().x() - self.padding) // self.tile)
        if 0 <= selected < len(self.items):
            self.selected = selected
            self.update()

    def mouseReleaseEvent(self, event):
        self.finish(True)

    def closeEvent(self, event):
        self.finish(False)
        event.ignore()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--opacity', type=int, default=67)
    parser.add_argument('--background', default='#dedede')
    parser.add_argument('--foreground', default='#1a1a1a')
    parser.add_argument('--font', default='Inter')
    parser.add_argument('--radius', type=int, default=20)
    args = parser.parse_args()
    app = QtWidgets.QApplication([sys.argv[0], '-name', 'GoldenGateSwitcher'])
    app.setQuitOnLastWindowClosed(False)
    overlay = Switcher(args)
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    app.aboutToQuit.connect(lambda: overlay.x11.x.XUngrabKeyboard(overlay.x11.display, 0))
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
