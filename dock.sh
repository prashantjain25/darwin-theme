#!/usr/bin/env bash
# Golden Gate Theme: auto-detect the active KDE or LXQt session.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$ROOT/lib/desktop.py" dock "$@"
