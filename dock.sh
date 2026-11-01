#!/usr/bin/env bash
# Golden Gate LXQt Theme: menu bar (top panel) and dock (bottom panel).
# Separate from the desktop look (./install.sh); both read config/theme.json.
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

WANT_BAR=1; WANT_DOCK=1; CONFIGURE=0; NO_RESTART=0
usage() {
  cat <<EOF
Usage: ./dock.sh [options]

Builds the menu bar (top panel, ${BAR_H}px) and the dock (bottom panel) from
config/theme.json. Backups are stored for ./restore.sh.

Options:
  --configure       interactive wizard first (dock apps, sizes, mode ...)
  --menubar-only    only the top menu bar
  --dock-only       only the dock
  (dock order and the separator "|" are set in config/theme.json: dock.apps)
  --install-deps    apt-install missing packages and fetch the WhiteSur icon theme
  --no-restart      do not restart the panel / picom
  --dry-run         print what would happen, change nothing
  -y, --yes
  -h, --help
EOF
}
while [ $# -gt 0 ]; do
  if parse_common_flag "$1"; then shift; continue; fi
  case "$1" in
    --configure) CONFIGURE=1;;
    --menubar-only) WANT_DOCK=0;;
    --dock-only) WANT_BAR=0;;
    --no-restart) NO_RESTART=1;;
    -h|--help) usage; exit 0;;
    *) usage; die "unknown option: $1";;
  esac; shift
done

[ "$CONFIGURE" = 1 ] && python3 "$REPO_DIR/lib/theme.py" configure
load_theme_config
[ "$BAR_ENABLED" = 1 ] || WANT_BAR=0
[ "$DOCK_ENABLED" = 1 ] || WANT_DOCK=0
[ "$WANT_BAR$WANT_DOCK" = 00 ] && die "menu bar and dock are both disabled in config/theme.json"
[ "$DRY_RUN" = 1 ] && warn "dry-run: nothing will be changed"
mkdir -p "$STATE_DIR" 2>/dev/null || true

# ---------------------------------------------------------------- dependencies
step "Checking dependencies"
for c in python3 lxqt-panel picom pcmanfm-qt; do need_cmd "$c"; done
ensure_whitesur_icons || true
finish_deps
ICON_DIR="$(whitesur_icon_dir || true)"
[ -n "$ICON_DIR" ] || warn "WhiteSur icon theme not found: dock launchers will use whatever icons the system offers"

# ---------------------------------------------------------------- launchers
APPS_DIR="$HOME/.local/share/applications"
DESKTOPS=()
SEP_AFTER=0

icon_path() { # icon_path <relative-file> <fallback-name>
  if [ -n "$ICON_DIR" ] && [ -f "$ICON_DIR/$1" ]; then echo "$ICON_DIR/$1"; else echo "$2"; fi
}

write_launcher() { # write_launcher <id> <name> <exec> <icon> [extra lines]
  local id="$1" name="$2" exec="$3" icon="$4" extra="${5:-}"
  local f="$APPS_DIR/golden-gate-dock-$id.desktop"
  backup "$f"
  if [ "$DRY_RUN" = 0 ]; then
    mkdir -p "$APPS_DIR"
    printf '[Desktop Entry]\nType=Application\nName=%s\nExec=%s\nIcon=%s\nTerminal=false\nCategories=Utility;\n%s\n' \
      "$name" "$exec" "$icon" "$extra" > "$f"
  fi
  DESKTOPS+=("$f"); info "launcher  $name"
}

first_cmd() { local c; for c in "$@"; do have "$c" && { echo "$c"; return 0; }; done; return 1; }

find_idea() {
  local c
  c="$(first_cmd idea intellij-idea-ultimate intellij-idea-community idea.sh || true)"; [ -n "$c" ] && { command -v "$c"; return 0; }
  for c in "$HOME"/Downloads/idea-I*/bin/idea.sh /opt/idea*/bin/idea.sh /opt/intellij*/bin/idea.sh \
           "$HOME/.local/share/JetBrains/Toolbox/scripts/idea" "$HOME"/opt/idea*/bin/idea.sh; do
    [ -x "$c" ] && { echo "$c"; return 0; }
  done
  return 1
}

build_launcher() { # build_launcher <id>   (ids: files browser settings trash downloads ide)
  local id="$1" x
  case "$id" in                               # aliases for older configs
    finder) id=files;; chrome) id=browser;; fdm) id=downloads;; idea) id=ide;;
  esac
  [[ " ${SEEN_APPS:-} " == *" $id "* ]] && return 0      # list the same app only once
  SEEN_APPS="${SEEN_APPS:-} $id"
  case "$id" in
    files)    have pcmanfm-qt && write_launcher files Files "pcmanfm-qt %U" "$(icon_path apps/scalable/system-file-manager.svg system-file-manager)" || warn "pcmanfm-qt missing: no file manager";;
    browser)  x="$(first_cmd google-chrome-stable google-chrome chromium chromium-browser firefox || true)"
              [ -n "$x" ] && write_launcher browser Browser "$x %U" "$(icon_path apps/scalable/google-chrome.svg web-browser)" || warn "no web browser found: skipped";;
    settings) have lxqt-config && write_launcher settings Settings "lxqt-config" "$(icon_path apps/scalable/systemsettings.svg preferences-system)" || warn "lxqt-config missing: skipped";;
    trash)    have pcmanfm-qt && write_launcher trash Trash "pcmanfm-qt trash:///" "$(icon_path places/scalable/user-trash.svg user-trash)" || true;;
    downloads) x="$(first_cmd freedownloadmanager fdm || true)"; [ -z "$x" ] && [ -x /opt/freedownloadmanager/fdm ] && x=/opt/freedownloadmanager/fdm
              if [ -n "$x" ]; then
                local ic=/opt/freedownloadmanager/icon.png; [ -f "$ic" ] || ic=download-manager
                write_launcher downloads Downloads "$x" "$ic"
              else warn "download manager not found: skipped"; fi;;
    ide)      x="$(find_idea || true)"
              [ -n "$x" ] && write_launcher ide IDE "$x %f" "$(icon_path apps/scalable/idea-ultimate.svg idea)" "StartupWMClass=jetbrains-idea" \
                          || warn "IDE not found: skipped";;
    *) warn "unknown dock app '$id' (known: files browser settings trash downloads ide)";;
  esac
}

if [ "$WANT_DOCK" = 1 ]; then
  step "Dock launchers"
  for id in $DOCK_APPS; do
    if [ "$id" = "|" ] || [ "$id" = separator ]; then SEP_AFTER=${#DESKTOPS[@]}; continue; fi
    build_launcher "$id"
  done
  [ "$SEP_AFTER" -ge "${#DESKTOPS[@]}" ] && SEP_AFTER=0   # a separator at the very end draws nothing
  # custom entries from config/theme.json: dock.custom = [{"name","exec","icon"}, ...]
  while IFS=$'\t' read -r cname cexec cicon; do
    [ -n "$cname" ] && write_launcher "custom-$(echo "$cname" | tr -c 'A-Za-z0-9' '-')" "$cname" "$cexec" "$cicon"
  done < <(python3 - <<PY
import sys; sys.path.insert(0, "$REPO_DIR/lib")
import theme
for c in theme.load()["dock"].get("custom", []):
    print("\t".join([c.get("name", ""), c.get("exec", ""), c.get("icon", "application-x-executable")]))
PY
  )
  [ "${#DESKTOPS[@]}" -gt 0 ] || die "no dock launchers could be created"
  # Figma dock: 9 px between items, 8 px edge padding; measured with the panel's own button margins
  if [ "$DOCK_W" = auto ]; then DOCK_W=$(( ${#DESKTOPS[@]} * (DOCK_ICON + 9) + 19 + (SEP_AFTER > 0 ? 8 : 0) )); fi
  info "dock width: ${DOCK_W}px for ${#DESKTOPS[@]} launchers"
fi

# ---------------------------------------------------------------- panel layout
step "Panel layout"
PANEL_CONF="$HOME/.config/lxqt/panel.conf"
backup "$PANEL_CONF"
[ "$DRY_RUN" = 1 ] || [ "$NO_RESTART" = 1 ] || { pkill -x lxqt-panel 2>/dev/null || true; sleep 2; }   # the panel rewrites its config on exit
ARGS=("$PANEL_CONF" --mode "$MODE" --bar-h "$BAR_H" --dock-h "$DOCK_H" --dock-icon "$DOCK_ICON" --dock-w "${DOCK_W:-290}" --clock-format "$CLOCK_FORMAT")
[ "$WANT_BAR" = 1 ] && ARGS+=(--menubar)
[ -n "$ICON_DIR" ] && [ -f "$ICON_DIR/places/16/start-here.svg" ] && ARGS+=(--start-icon "$ICON_DIR/places/16/start-here.svg")
if [ "$WANT_DOCK" = 1 ]; then ARGS+=(--dock --sep-after "$SEP_AFTER"); for d in "${DESKTOPS[@]}"; do ARGS+=(--app "$d"); done; fi
run python3 "$REPO_DIR/lib/panel.py" "${ARGS[@]}"

# separator line drawn by the panel's "lined" spacer: Figma's 11 x 41 dock separator
if [ "$WANT_DOCK" = 1 ] && [ "$SEP_AFTER" -gt 0 ] && [ -d "$HOME/.local/share/lxqt/themes/sombre-et-rond/spacer-plugin" ]; then
  install_file "$REPO_DIR/assets/dock/dock-separator.svg" "$HOME/.local/share/lxqt/themes/sombre-et-rond/spacer-plugin/spacer-line.svg"
fi

# ---------------------------------------------------------------- stylesheet + compositor
step "Stylesheet and compositor rules"
[ "$WANT_BAR" = 1 ]  && state_set MENUBAR 1
[ "$WANT_DOCK" = 1 ] && state_set DOCK 1
compose_panel_qss
render "$REPO_DIR/assets/picom/picom.conf.in" "$HOME/.config/picom.conf"

if [ "$NO_RESTART" = 0 ]; then
  step "Restarting picom and the panel"
  restart_picom; restart_panel
fi

step "Done"
info "Backups: $BACKUP_DIR   (undo with ./restore.sh)"
[ "$WANT_BAR" = 1 ]  && info "Menu bar: ${BAR_H}px, start icon, tray, one-line clock."
[ "$WANT_DOCK" = 1 ] && info "Dock: ${#DESKTOPS[@]} launchers, ${DOCK_ICON}px icons."
info "Limitation: LXQt has no global-menu host, so app menus (File/Edit) stay inside windows."
