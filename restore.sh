#!/usr/bin/env bash
# Undo ./install.sh and ./dock.sh using the backups they recorded.
#   ./restore.sh --list          show available backups
#   ./restore.sh                 restore the most recent run
#   ./restore.sh 20250101-120000 restore a specific run
#   ./restore.sh all             restore every run, newest first (back to the original state)
#   add --no-restart to skip restarting picom / panel / openbox
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

list() { ls -1 "$BACKUP_ROOT" 2>/dev/null | sort || true; }

restore_one() {
  local dir="$BACKUP_ROOT/$1" kind path
  [ -f "$dir/manifest.txt" ] || die "no backup named '$1' (see --list)"
  step "Restoring $1"
  # reverse order so later edits of the same file unwind correctly
  tac "$dir/manifest.txt" | while read -r kind path; do
    case "$kind" in
      BAK) run mkdir -p "$(dirname "$path")"; run rm -rf "$path"; run cp -a "$dir$path" "$path"; info "restored $path";;
      NEW) run rm -rf "$path"; info "removed  $path (did not exist before)";;
    esac
  done
}

while [ $# -gt 0 ]; do case "$1" in --no-restart) GG_NO_RESTART=1; shift;; *) break;; esac; done
case "${1:-latest}" in
  --list|-l) list; exit 0;;
  -h|--help) sed -n '2,6p' "$0"; exit 0;;
  --dry-run) DRY_RUN=1; shift; set -- "${1:-latest}";;
esac
case "${1:-latest}" in
  latest) t="$(list | tail -1)"; [ -n "$t" ] || die "no backups found in $BACKUP_ROOT"; restore_one "$t";;
  all) for t in $(list | sort -r); do restore_one "$t"; done;;
  *) restore_one "$1";;
esac
restart_picom; restart_panel; reconfigure_openbox
info "Restored. Log out and back in (or restart apps) for Qt/GTK settings to reload."
