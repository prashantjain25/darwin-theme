"""Pure-Python search/calculation logic; no Qt dependency and no shell execution.
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import ast
import math
import operator
import configparser
from dataclasses import dataclass
import locale
import os
from pathlib import Path
import shutil
import hashlib
import json
import re
import subprocess
import time


_CONVERT = re.compile(r"^\s*([0-9][0-9,._]*)?\s*([A-Za-z]{3})\s+(?:to|in|into|->|=)\s+([A-Za-z]{3})\s*$")
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def looks_like_math(query: str) -> bool:
    return bool(re.fullmatch(r"[0-9\s.+\-*/()^%]+", query)) and any(op in query for op in "+-*/^%")


def looks_like_conversion(query: str) -> bool:
    return bool(_CONVERT.match(query)) or bool(shutil.which("qalc") and re.search(r"\s(to|in)\s", query))


def ecb_rates(cache_dir=None, now=None, fetch=None, timeout: float = 3.0):
    """Euro foreign-exchange reference rates (no API key, no extra package); cached for 12 h."""
    cache = Path(cache_dir or Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "darwin-spotlight") / "ecb-rates.json"
    now = time.time() if now is None else now
    cached = None
    try:
        cached = json.loads(cache.read_text())
        if now - cached["time"] < 12 * 3600:
            return cached["rates"]
    except (OSError, ValueError, KeyError, TypeError):
        cached = None
    try:
        if fetch is None:
            import urllib.request
            with urllib.request.urlopen(ECB_URL, timeout=timeout) as response:
                text = response.read(200_000).decode("utf-8", "replace")
        else:
            text = fetch()
        rates = {code: float(rate) for code, rate in re.findall(r"currency=['\"]([A-Z]{3})['\"]\s+rate=['\"]([0-9.]+)['\"]", text)}
        if not rates:
            raise ValueError("no rates")
        rates["EUR"] = 1.0
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"time": now, "rates": rates}))
        return rates
    except (OSError, ValueError):
        return cached["rates"] if cached else None   # stale rates beat no answer when offline


def convert_currency(text: str, rates=None) -> str | None:
    match = _CONVERT.match(text)
    if not match:
        return None
    amount_text, source, target = match.groups()
    try:
        amount = float((amount_text or "1").replace(",", ""))
    except ValueError:
        return None
    rates = rates if rates is not None else ecb_rates()
    source, target = source.upper(), target.upper()
    if not rates or source not in rates or target not in rates or not math.isfinite(amount) or abs(amount) > 1e15:
        return None
    return f"{amount * rates[target] / rates[source]:,.2f} {target}"


def qalc_result(text: str, timeout: float = 3.0) -> str | None:
    """libqalculate when installed: units, functions and currencies, as in the LXQt launcher."""
    if not shutil.which("qalc") or not text or text.startswith("-") or len(text) > 256:
        return None
    try:
        out = subprocess.run(["qalc", "-t", text], capture_output=True, text=True, errors="replace", timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = out.strip().splitlines()[0].strip() if out.strip() else ""
    return line if line and not line.lower().startswith(("error", "warning")) else None


def evaluate_expression(text: str) -> str | None:
    """Arithmetic first (instant, bounded), then qalc, then built-in currency conversion."""
    return calculate(text) or qalc_result(text) or convert_currency(text)


def find_files(query: str, roots=None, limit: int = 7, cancelled=None,
               use_indexes: bool = True, timeout: float = 0.8) -> list[Path]:
    """Filename search for a worker thread. Never walk the entire home directory.

    Prefer Baloo, then plocate. Each subprocess has a hard timeout and a result
    cap. Fallback visits at most 1500 entries / two levels in known folders.
    No file contents are read. Empty queries never expose recent/private names.
    """
    query = query.strip()
    if not query or len(query) > 256 or limit <= 0:
        return []
    deadline = time.monotonic() + timeout
    def stopped():
        return time.monotonic() >= deadline or (cancelled is not None and cancelled.is_set())
    if stopped():
        return []
    home = Path.home()
    search_roots = [Path(p).absolute() for p in roots] if roots is not None else [home]
    found = []
    def accept(path):
        path = Path(path)
        if (path.is_absolute() and query.casefold() in path.name.casefold()
                and any(path.is_relative_to(root) for root in search_roots)
                and path.exists() and path not in found):
            found.append(path)

    if use_indexes:
        commands = []
        if shutil.which("baloosearch"):
            commands.append(["baloosearch", "--limit", "64", "--", query])
        if shutil.which("plocate"):
            # Escape glob syntax: treat input as a literal filename fragment.
            literal = "".join("[" + c + "]" if c in "*?[]" else c for c in query)
            commands.append(["plocate", "-i", "-b", "-l", "128", "--", "*" + literal + "*"])
        for command in commands:
            if stopped():
                return found[:limit]
            try:
                result = subprocess.run(command, capture_output=True, text=True,
                                        errors="replace", timeout=max(.01, min(.35, deadline - time.monotonic())))
                for line in result.stdout.splitlines():
                    if stopped():
                        break
                    if line.startswith("/"):
                        accept(line)
                        if len(found) >= limit:
                            return found[:limit]
            except (OSError, subprocess.TimeoutExpired):
                pass

    fallback_roots = search_roots if roots is not None else [home / folder for folder in ("Desktop", "Documents", "Downloads")]
    pending = [(root, 0) for root in fallback_roots]
    visited = 0
    while pending and visited < 1500 and not stopped():
        directory, depth = pending.pop(0)
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    visited += 1
                    if visited > 1500 or stopped():
                        break
                    accept(entry.path)
                    if len(found) >= limit:
                        return found[:limit]
                    if depth < 2 and not entry.name.startswith(".") and entry.is_dir(follow_symlinks=False):
                        pending.append((Path(entry.path), depth + 1))
        except OSError:
            continue
    return found[:limit]


@dataclass(frozen=True)
class Application:
    name: str
    desktop_file: str
    icon: str = "application-x-executable"
    keywords: str = ""


def load_applications(directories=None, current_desktop=None) -> list[Application]:
    """Index XDG desktop files, respecting user overrides and desktop visibility.

    Exec is never parsed here. Gio owns field codes, quoting, DBus activation and
    Terminal/Path semantics at launch time.
    """
    if directories is None:
        data_home = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
        data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
        directories = [Path(d) / "applications" for d in [data_home, *data_dirs.split(":")] if d]
    desktops = set((current_desktop if current_desktop is not None else os.environ.get("XDG_CURRENT_DESKTOP", "KDE")).split(":"))
    language = (locale.getlocale()[0] or "").split(".")[0]
    seen, apps = set(), []
    for directory in directories:
        directory = Path(directory)
        for path in sorted(directory.rglob("*.desktop")):
            desktop_id = str(path.relative_to(directory)).replace(os.sep, "-")
            if desktop_id in seen:
                continue
            seen.add(desktop_id)
            config = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                config.read(path, encoding="utf-8")
                entry = config["Desktop Entry"]
                if entry.get("Type") != "Application" or entry.getboolean("Hidden", False) or entry.getboolean("NoDisplay", False):
                    continue
                only = set(filter(None, entry.get("OnlyShowIn", "").split(";")))
                exclude = set(filter(None, entry.get("NotShowIn", "").split(";")))
                if (only and not only & desktops) or exclude & desktops:
                    continue
                if entry.get("TryExec") and not shutil.which(entry["TryExec"]):
                    continue
                if not entry.get("Exec") and not entry.getboolean("DBusActivatable", False):
                    continue
                name = entry.get(f"Name[{language}]", entry.get(f"Name[{language.split('_')[0]}]", entry.get("Name", "")))
                if not name:
                    continue
                keywords = " ".join(entry.get(k, "") for k in ("GenericName", "Keywords", "Comment"))
                apps.append(Application(name, str(path.absolute()), entry.get("Icon", "application-x-executable"), keywords))
            except (OSError, UnicodeError, configparser.Error, ValueError, KeyError):
                continue
    return sorted(apps, key=lambda app: app.name.casefold())


def _default_directories():
    data_home = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
    data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    return [Path(d) / "applications" for d in [data_home, *data_dirs.split(":")] if d]


def load_applications_cached(cache_dir=None, directories=None, current_desktop=None) -> list[Application]:
    """Same result as load_applications, but reuses a saved list until a .desktop file changes.

    The key is every .desktop file's path and modification time (about 5 ms to compute), so installing,
    removing or editing an application refreshes the list. Any cache problem falls back to a full scan.
    """
    directories = [Path(d) for d in (directories if directories is not None else _default_directories())]
    desktop = current_desktop if current_desktop is not None else os.environ.get("XDG_CURRENT_DESKTOP", "KDE")
    items = []
    for directory in directories:
        try:
            for path in directory.rglob("*.desktop"):
                try:
                    items.append((str(path), path.stat().st_mtime_ns))
                except OSError:
                    pass
        except OSError:
            pass
    key = hashlib.sha256(json.dumps([sorted(items), desktop, locale.getlocale()[0] or ""]).encode()).hexdigest()
    cache = Path(cache_dir or Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "darwin-spotlight") / "apps.json"
    try:
        data = json.loads(cache.read_text())
        if data.get("key") == key:
            return [Application(**app) for app in data["apps"]]
    except (OSError, ValueError, TypeError, KeyError):
        pass
    apps = load_applications(directories, current_desktop)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": key, "apps": [vars(app) for app in apps]}))
    except OSError:
        pass
    return apps


def search_applications(apps, query: str, limit: int = 7) -> list[Application]:
    words = query.casefold().split()
    def score(app):
        name = app.name.casefold()
        needle = query.strip().casefold()
        if not all(word in name + " " + app.keywords.casefold() for word in words):
            return None
        return (0 if name == needle else 1 if name.startswith(needle) else 2 if needle in name else 3, name)
    matches = [(score(app), app) for app in apps]
    return [app for rank, app in sorted((item for item in matches if item[0] is not None), key=lambda item: item[0])][:max(0, limit)]


_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
           ast.Mod: operator.mod, ast.Pow: operator.pow}


def calculate(text: str) -> str | None:
    """Small arithmetic only. Bound input, AST work, exponents and intermediates."""
    text = text.strip().removeprefix("=").strip().replace("^", "**")
    if not text or len(text) > 256:
        return None
    try:
        tree = ast.parse(text, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 64:
            return None

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                value = node.value
            elif isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
                value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
            elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Pow) and abs(right) > 100:
                    raise ValueError("Exponent too large")
                value = _BINARY[type(node.op)](left, right)
            else:
                raise ValueError("Not arithmetic")
            if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e100:
                raise ValueError("Result out of range")
            return value

        result = visit(tree.body)
        return str(result) if isinstance(result, int) else format(result, ".12g")
    except (ValueError, SyntaxError, OverflowError, ZeroDivisionError, TypeError, RecursionError):
        return None
