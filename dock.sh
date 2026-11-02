#!/usr/bin/env bash
# Golden Gate LXQt Theme: menu bar (top panel) and dock (bottom panel).
# Separate from the desktop look (./install.sh); both read config/theme.json.
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

WANT_BAR=1; WANT_DOCK=1; CONFIGURE=0; NO_RESTART=0; DOCK_MODE_FLAG=""
usage() {
  cat <<EOF
Usage: ./dock.sh [options]

Builds the menu bar (top panel, ${BAR_H}px) and the dock (bottom panel) from
config/theme.json. Backups are stored for ./restore.sh.

Options:
  --configure       interactive wizard first (dock apps, sizes, mode ...)
  --dock-mode MODE  switch how the dock behaves, saves it in config/theme.json and returns at once:
                      reserve           reserves its space, windows never cover it (default)
                      always-on-top     floats above windows, reserves nothing
                      intelligent-hide  hides only while a window overlaps it
                      auto-hide         always hidden, hit the screen edge to show it
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
    --dock-mode) [ $# -ge 2 ] || die "--dock-mode needs a value"; DOCK_MODE_FLAG="$2"; shift;;
    --menubar-only) WANT_DOCK=0;;
    --dock-only) WANT_BAR=0;;
    --no-restart) NO_RESTART=1;;
    -h|--help) usage; exit 0;;
    *) usage; die "unknown option: $1";;
  esac; shift
done

[ "$CONFIGURE" = 1 ] && python3 "$REPO_DIR/lib/theme.py" configure
load_theme_config

if [ -n "$DOCK_MODE_FLAG" ]; then
  step "Switching the dock behaviour"
  [ "$DRY_RUN" = 1 ] && info "[dry-run] theme.py set dock.mode $DOCK_MODE_FLAG" || python3 "$REPO_DIR/lib/theme.py" set dock.mode "$DOCK_MODE_FLAG" || die "invalid dock mode '$DOCK_MODE_FLAG'"
  load_theme_config
  info "dock mode: $DOCK_MODE (backend: $DOCK_BACKEND)"
  if [ "$DOCK_BACKEND" = plank ]; then
    case "$DOCK_MODE" in intelligent-hide) HM=intelligent;; auto-hide) HM=auto;; *) HM=none;; esac
    PR=false; [ "$DOCK_MODE" = auto-hide ] && PR=true
    if have gsettings && [ "${GG_SKIP_GSETTINGS:-0}" != 1 ] && [ "$DRY_RUN" = 0 ]; then
      gsettings set net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ hide-mode "'$HM'"
      gsettings set net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ pressure-reveal "$PR"
    else info "[skipped] gsettings hide-mode=$HM pressure-reveal=$PR"; fi
  else
    PANEL_CONF="$HOME/.config/lxqt/panel.conf"; backup "$PANEL_CONF"
    [ "$DRY_RUN" = 1 ] || [ "$NO_RESTART" = 1 ] || { pkill -x lxqt-panel 2>/dev/null || true; sleep 2; }
    run python3 "$REPO_DIR/lib/panel.py" "$PANEL_CONF" --mode-only --dock-mode "$DOCK_MODE"
    [ "$NO_RESTART" = 1 ] || restart_panel
  fi
  step "Done"; info "undo with ./restore.sh, switch again with ./dock.sh --dock-mode <mode>"
  exit 0
fi

# Plank is only used when it is installed; otherwise keep the LXQt dock so the screen edge never goes empty
if [ "$DOCK_BACKEND" = plank ] && ! have plank; then
  warn "dock.backend is 'plank' but plank is not installed: using the LXQt dock instead"
  DOCK_BACKEND=lxqt-panel
fi
[ "$BAR_ENABLED" = 1 ] || WANT_BAR=0
[ "$DOCK_ENABLED" = 1 ] || WANT_DOCK=0
[ "$WANT_BAR$WANT_DOCK" = 00 ] && die "menu bar and dock are both disabled in config/theme.json"
[ "$DRY_RUN" = 1 ] && warn "dry-run: nothing will be changed"
mkdir -p "$STATE_DIR" 2>/dev/null || true

# ---------------------------------------------------------------- dependencies
step "Checking dependencies"
for c in python3 lxqt-panel picom pcmanfm-qt; do need_cmd "$c"; done
ensure_whitesur_icons || true
if [ "$DOCK_BACKEND" = plank ] && [ "$DOCK_ENABLED" = 1 ] && [ "$WANT_DOCK" = 1 ]; then need_cmd plank; PKG[plank]=plank; fi
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
  if [ "$DOCK_BACKEND" = lxqt-panel ]; then
    info "dock backend: lxqt-panel. Applied: fill $DOCK_FILL at $DOCK_OPACITY%, padding/width, separator."
    info "Not possible with the panel (its window is drawn opaque): border, outer ring, radius $DOCK_RADIUS, ${DOCK_OFFSET}px edge offset, blur."
    info "Set dock.backend to \"plank\" in config/theme.json to enable them (sudo apt install plank)."
  fi
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
  # each item takes ICON+GAP (the panel's own spacing); the panel supplies the left edge, so the width
  # adds nothing after the last item (measured: equal visible padding on both sides)
  if [ "$DOCK_W" = auto ]; then DOCK_W=$(( ${#DESKTOPS[@]} * (DOCK_ICON + DOCK_GAP) + (SEP_AFTER > 0 ? DOCK_SEP_PAD : 0) )); fi
  info "dock: ${DOCK_W}x${DOCK_H} px, ${DOCK_ICON} px icons (scale ${DOCK_SCALE} for this screen)"
fi

# ---------------------------------------------------------------- panel layout
step "Panel layout"
PANEL_CONF="$HOME/.config/lxqt/panel.conf"
backup "$PANEL_CONF"
[ "$DRY_RUN" = 1 ] || [ "$NO_RESTART" = 1 ] || { pkill -x lxqt-panel 2>/dev/null || true; sleep 2; }   # the panel rewrites its config on exit
ARGS=("$PANEL_CONF" --mode "$MODE" --dock-mode "$DOCK_MODE" --hide-tray "$HIDE_TRAY" --drives "$SHOW_DRIVES" --clock-semibold "$CLOCK_SEMIBOLD" \
      --dock-fill "$DOCK_FILL" --dock-opacity "$DOCK_OPACITY" --bar-h "$BAR_H" --dock-h "$DOCK_H" --dock-icon "$DOCK_ICON" --dock-w "${DOCK_W:-290}" --clock-format "$CLOCK_FORMAT")
[ "$WANT_BAR" = 1 ] && ARGS+=(--menubar)
[ -n "$ICON_DIR" ] && [ -f "$ICON_DIR/places/16/start-here.svg" ] && ARGS+=(--start-icon "$ICON_DIR/places/16/start-here.svg")
if [ "$WANT_DOCK" = 1 ]; then
  ARGS+=(--dock --sep-after "$SEP_AFTER"); for d in "${DESKTOPS[@]}"; do ARGS+=(--app "$d"); done
  [ "$DOCK_BACKEND" = plank ] && ARGS+=(--no-dock-panel)
fi
run python3 "$REPO_DIR/lib/panel.py" "${ARGS[@]}"

# Plank backend: theme, pinned launchers, dock settings, autostart
if [ "$WANT_DOCK" = 1 ] && [ "$DOCK_BACKEND" = plank ]; then
  step "Plank dock"
  backup "$HOME/.local/share/plank/themes/GoldenGate"; backup "$HOME/.config/plank/dock1/launchers"
  PA=(--home "$HOME" --mode "$MODE" --dock-mode "$DOCK_MODE" --icon-size "$DOCK_ICON" --fill "$DOCK_FILL" --opacity "$DOCK_OPACITY" \
      --border "$DOCK_BORDER" --ring "$DOCK_RING" --radius "$DOCK_RADIUS" --padding "$DOCK_PADDING")
  for d in "${DESKTOPS[@]}"; do PA+=(--app "$d"); done
  if [ "$DRY_RUN" = 1 ]; then info "[dry-run] python3 lib/plank.py ${PA[*]}"; else
    SETTINGS="$(python3 "$REPO_DIR/lib/plank.py" "${PA[@]}")"
    if have gsettings && [ "${GG_SKIP_GSETTINGS:-0}" != 1 ]; then
      while IFS=$'\t' read -r k v; do
        gsettings set net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ "$k" "$v" 2>/dev/null || warn "plank setting $k not applied (is plank installed?)"
      done <<<"$SETTINGS"
    else info "(gsettings skipped)"; fi
  fi
  backup "$HOME/.config/autostart/plank.desktop"
  if [ "$DRY_RUN" = 0 ]; then
    mkdir -p "$HOME/.config/autostart"
    printf '[Desktop Entry]\nType=Application\nName=Plank\nExec=plank\nX-GNOME-Autostart-enabled=true\n' > "$HOME/.config/autostart/plank.desktop"
  fi
  [ "$DOCK_OFFSET" -gt 0 ] && info "note: Plank cannot float the dock ${DOCK_OFFSET}px above the screen edge; the separator is not drawn either."
  [ "$DOCK_BLUR" = 1 ] || DOCK_BLUR_EXCLUDE=", \"class_g = 'Plank'\""
fi

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
  if [ "$WANT_DOCK" = 1 ] && [ "$DOCK_BACKEND" = plank ] && [ "$DRY_RUN" = 0 ] && have plank; then
    pkill -x plank 2>/dev/null || true; sleep 1; ( setsid nohup plank >/dev/null 2>&1 & )
  fi
fi

step "Done"
info "Backups: $BACKUP_DIR   (undo with ./restore.sh)"
[ "$WANT_BAR" = 1 ]  && info "Menu bar: ${BAR_H}px, start icon, tray, one-line clock."
[ "$WANT_DOCK" = 1 ] && info "Dock: ${#DESKTOPS[@]} launchers, ${DOCK_ICON}px icons, behaviour: $DOCK_MODE."
info "Limitation: LXQt has no global-menu host, so app menus (File/Edit) stay inside windows."
