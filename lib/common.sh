#!/usr/bin/env bash
# Shared helpers for install.sh / dock.sh / restore.sh
# shellcheck shell=bash

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/golden-gate-lxqt-theme"
BACKUP_ROOT="$STATE_DIR/backups"
STATE_FILE="$STATE_DIR/state"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$STAMP"

# Layout constants (Figma menu bar / dock); picom rules are rendered from these
BAR_H="${BAR_H:-34}"
DOCK_H="${DOCK_H:-62}"
DOCK_ICON="${DOCK_ICON:-36}"
DOCK_W="${DOCK_W:-290}"
WIN_R="${WIN_R:-17}"
MENU_R="${MENU_R:-14}"

DRY_RUN=0
ASSUME_YES=0
INSTALL_DEPS=0

# ---------------------------------------------------------------- logging
if [ -t 1 ]; then C_B=$'\e[1m'; C_G=$'\e[32m'; C_Y=$'\e[33m'; C_R=$'\e[31m'; C_0=$'\e[0m'; else C_B=; C_G=; C_Y=; C_R=; C_0=; fi
step() { printf '%s==>%s %s%s%s\n' "$C_G" "$C_0" "$C_B" "$*" "$C_0"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '%s[warn]%s %s\n' "$C_Y" "$C_0" "$*" >&2; }
die()  { printf '%s[error]%s %s\n' "$C_R" "$C_0" "$*" >&2; exit 1; }

# run a command, or just print it in --dry-run mode
run() {
  if [ "$DRY_RUN" = 1 ]; then printf '    [dry-run] %s\n' "$*"; else "$@"; fi
}

confirm() {
  [ "$ASSUME_YES" = 1 ] && return 0
  read -r -p "$1 [y/N] " a; [ "$a" = y ] || [ "$a" = Y ]
}

parse_common_flag() { # returns 0 if flag consumed
  case "$1" in
    --dry-run) DRY_RUN=1;;
    -y|--yes) ASSUME_YES=1;;
    --install-deps) INSTALL_DEPS=1;;
    *) return 1;;
  esac
}

# ---------------------------------------------------------------- backups
# backup <path>: copy an existing file/dir into the timestamped backup dir and
# record it so restore.sh can undo. Paths that do not exist yet are recorded as NEW.
backup() {
  local p="$1"
  [ "$DRY_RUN" = 1 ] && { info "[dry-run] backup $p"; return 0; }
  mkdir -p "$BACKUP_DIR"
  if [ -e "$p" ] || [ -L "$p" ]; then
    mkdir -p "$BACKUP_DIR$(dirname "$p")"
    cp -a "$p" "$BACKUP_DIR$p"
    echo "BAK $p" >> "$BACKUP_DIR/manifest.txt"
  else
    echo "NEW $p" >> "$BACKUP_DIR/manifest.txt"
  fi
}

# install_file <src> <dst>: back up dst, then copy
install_file() {
  local src="$1" dst="$2"
  backup "$dst"
  run mkdir -p "$(dirname "$dst")"
  run cp -a "$src" "$dst"
}

# render <template> <dest>: substitute @VARS@ and write
render() {
  local src="$1" dst="$2"
  backup "$dst"
  run mkdir -p "$(dirname "$dst")"
  if [ "$DRY_RUN" = 1 ]; then info "[dry-run] render $src -> $dst"; return 0; fi
  local switcher_alpha dock_blur_bool=true
  switcher_alpha="$(python3 -c "print(${SWITCHER_OPACITY:-67} / 100)")"
  [ "${DOCK_BLUR:-1}" = 1 ] || dock_blur_bool=false
  sed -e "s|@SWITCHER_ALPHA@|$switcher_alpha|g" -e "s|@DOCK_BLUR_BOOL@|$dock_blur_bool|g" -e "s|@HOME@|$HOME|g" -e "s|@BAR_H@|$BAR_H|g" -e "s|@DOCK_H@|$DOCK_H|g" \
      -e "s|@DOCK_OPACITY@|${DOCK_OPACITY:-39}|g" -e "s|@DOCK_ICON@|$DOCK_ICON|g" -e "s|@DOCK_W@|$DOCK_W|g" \
      -e "s|@WIN_R@|$WIN_R|g" -e "s|@MENU_R@|$MENU_R|g" \
      -e "s|@SWITCHER_OPACITY@|${SWITCHER_OPACITY:-67}|g" -e "s|@SWITCHER_R@|${SWITCHER_R:-20}|g" \
      -e "s|@DOCK_BLUR_EXCLUDE@|${DOCK_BLUR_EXCLUDE:-}|g" "$src" > "$dst"
}

# ---------------------------------------------------------------- state
state_get() { [ -f "$STATE_FILE" ] && sed -n "s/^$1=//p" "$STATE_FILE" | tail -1 || true; }
state_set() {
  [ "$DRY_RUN" = 1 ] && return 0
  mkdir -p "$STATE_DIR"; touch "$STATE_FILE"
  grep -v "^$1=" "$STATE_FILE" > "$STATE_FILE.tmp" || true
  echo "$1=$2" >> "$STATE_FILE.tmp"; mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# ---------------------------------------------------------------- dependencies
have() { command -v "$1" >/dev/null 2>&1; }

# command -> apt package (Debian/Ubuntu/Lubuntu names)
declare -A PKG=(
  [python3]=python3 [curl]=curl [unzip]=unzip [git]=git
  [fc-cache]=fontconfig [fc-list]=fontconfig
  [openbox]=openbox [picom]=picom
  [lxqt-panel]=lxqt-panel [pcmanfm-qt]=pcmanfm-qt
  [kvantummanager]=qt5-style-kvantum
  [gresource]=libglib2.0-bin [gsettings]=libglib2.0-bin
  [glib-compile-resources]=libglib2.0-dev-bin
  [gtk-update-icon-cache]=libgtk-3-bin
  [xprop]=x11-utils [xwininfo]=x11-utils
)
MISSING_PKGS=()
MISSING_NOTES=()

# need_cmd <cmd> [required|optional]
need_cmd() {
  local c="$1" kind="${2:-required}"
  if have "$c"; then info "ok       $c"; return 0; fi
  if [ "$kind" = optional ]; then info "optional $c (not found, feature skipped)"; return 0; fi
  info "MISSING  $c  (apt: ${PKG[$c]:-?})"
  MISSING_PKGS+=("${PKG[$c]:-$c}")
}

need_path() { # need_path <label> <note> <path>...
  local label="$1" note="$2"; shift 2
  local p
  for p in "$@"; do [ -e "$p" ] && { info "ok       $label ($p)"; return 0; }; done
  info "MISSING  $label"
  MISSING_NOTES+=("$label: $note")
  return 1
}

qt_style_plugins() {
  local p5 p6
  p5="$(ls /usr/lib/*/qt5/plugins/styles/libkvantum.so 2>/dev/null | head -1 || true)"
  p6="$(ls /usr/lib/*/qt6/plugins/styles/libkvantum.so 2>/dev/null | head -1 || true)"
  [ -n "$p5" ] && info "ok       Kvantum Qt5 style" || { info "MISSING  Kvantum Qt5 style (apt: qt5-style-kvantum)"; MISSING_PKGS+=(qt5-style-kvantum); }
  [ -n "$p6" ] && info "ok       Kvantum Qt6 style" || { info "MISSING  Kvantum Qt6 style (apt: qt6-style-kvantum)"; MISSING_PKGS+=(qt6-style-kvantum); }
}

# finish_deps: install (with --install-deps) or print what is missing, abort if required things are missing
finish_deps() {
  if [ "${#MISSING_PKGS[@]}" -gt 0 ]; then
    local uniq; uniq="$(printf '%s\n' "${MISSING_PKGS[@]}" | sort -u | tr '\n' ' ')"
    if [ "$INSTALL_DEPS" = 1 ]; then
      step "Installing missing packages: $uniq"
      run sudo apt-get install -y $uniq
    else
      warn "Missing packages. Install with:  sudo apt install $uniq"
      warn "or re-run with --install-deps to let this script do it."
      [ "$DRY_RUN" = 1 ] || die "Required dependencies are missing."
    fi
  fi
  if [ "${#MISSING_NOTES[@]}" -gt 0 ]; then
    local n; for n in "${MISSING_NOTES[@]}"; do warn "$n"; done
  fi
}

# ---------------------------------------------------------------- WhiteSur themes
WHITESUR_GTK_URL="https://github.com/vinceliuice/WhiteSur-gtk-theme.git"
WHITESUR_ICON_URL="https://github.com/vinceliuice/WhiteSur-icon-theme.git"

whitesur_gtk_dir() {
  local n="${1:-WhiteSur-Dark}" d
  for d in "$HOME/.themes/$n" "$HOME/.local/share/themes/$n" "/usr/share/themes/$n"; do
    [ -d "$d/gtk-3.0" ] && { echo "$d"; return 0; }
  done
  return 1
}

whitesur_icon_dir() {
  local d
  for d in "$HOME/.local/share/icons/WhiteSur-dark" "$HOME/.icons/WhiteSur-dark" /usr/share/icons/WhiteSur-dark; do
    [ -d "$d" ] && { echo "$d"; return 0; }
  done
  return 1
}

ensure_whitesur_gtk() { # ensure_whitesur_gtk [WhiteSur-Dark|WhiteSur-Light]
  local n="${1:-WhiteSur-Dark}" color=Dark; [ "$n" = WhiteSur-Light ] && color=Light
  whitesur_gtk_dir "$n" >/dev/null && return 0
  if [ "$INSTALL_DEPS" = 1 ]; then
    step "Installing WhiteSur GTK theme ($color) into ~/.themes"
    local t; t="$(mktemp -d)"
    run git clone --depth 1 "$WHITESUR_GTK_URL" "$t/gtk"
    run bash -c "cd '$t/gtk' && ./install.sh -c $color -o normal"
    rm -rf "$t"
  else
    MISSING_NOTES+=("$n GTK theme: git clone $WHITESUR_GTK_URL && cd WhiteSur-gtk-theme && ./install.sh -c $color   (or run with --install-deps)")
  fi
}

ensure_whitesur_icons() {
  whitesur_icon_dir >/dev/null && return 0
  if [ "$INSTALL_DEPS" = 1 ]; then
    step "Installing WhiteSur icon theme into ~/.local/share/icons"
    local t; t="$(mktemp -d)"
    run git clone --depth 1 "$WHITESUR_ICON_URL" "$t/icons"
    run bash -c "cd '$t/icons' && ./install.sh"
    rm -rf "$t"
  else
    MISSING_NOTES+=("WhiteSur icon theme: git clone $WHITESUR_ICON_URL && cd WhiteSur-icon-theme && ./install.sh   (or run with --install-deps)")
  fi
}

# ---------------------------------------------------------------- session helpers
restart_picom() {
  [ "${GG_NO_RESTART:-0}" = 1 ] && { info "(restart skipped)"; return 0; }
  [ "$DRY_RUN" = 1 ] && { info "[dry-run] restart picom"; return 0; }
  have picom || return 0
  pkill -x picom 2>/dev/null || true; sleep 1
  ( setsid nohup picom --config "$HOME/.config/picom.conf" >/dev/null 2>&1 & )
}

restart_panel() {
  [ "${GG_NO_RESTART:-0}" = 1 ] && { info "(restart skipped)"; return 0; }
  [ "$DRY_RUN" = 1 ] && { info "[dry-run] restart lxqt-panel"; return 0; }
  have lxqt-panel || return 0
  pkill -x lxqt-panel 2>/dev/null || true; sleep 2
  ( setsid nohup lxqt-panel >/dev/null 2>&1 & )
}

reconfigure_openbox() {
  [ "${GG_NO_RESTART:-0}" = 1 ] && { info "(restart skipped)"; return 0; }
  [ "$DRY_RUN" = 1 ] && { info "[dry-run] openbox --reconfigure"; return 0; }
  have openbox && openbox --reconfigure 2>/dev/null || true
}

# Compose the LXQt panel stylesheet: base + (menu bar block) + (dock block), by state flags
compose_panel_qss() {
  local theme_dir="$HOME/.local/share/lxqt/themes/sombre-et-rond"
  local out="$theme_dir/lxqt-panel.qss" tmp
  [ -d "$theme_dir" ] || return 0
  backup "$out"
  if [ "$DRY_RUN" = 1 ]; then info "[dry-run] compose $out"; return 0; fi
  tmp="$(mktemp)"
  { cat "$REPO_DIR/assets/lxqt/lxqt-panel.base.qss"
    [ "$(state_get MENUBAR)" = 1 ] && { echo; cat "$REPO_DIR/assets/dock/menubar.qss"; }
    [ "$(state_get DOCK)" = 1 ]    && { echo; cat "$REPO_DIR/assets/dock/dock.qss"; }
    true
  } > "$tmp"
  python3 "$REPO_DIR/lib/theme.py" transform "$tmp" "$out"; rm -f "$tmp"
}

# ---------------------------------------------------------------- theme config
# load_theme_config: eval the resolved values of config/theme.json (+defaults) into shell variables
load_theme_config() {
  python3 "$REPO_DIR/lib/theme.py" validate || die "Fix the errors in config/theme.json (or delete it to use the defaults)."
  eval "$(python3 "$REPO_DIR/lib/theme.py" env)"
  # Discover schemas installed with a user-local dock package.
  local user_schemas="${XDG_DATA_HOME:-$HOME/.local/share}/glib-2.0/schemas"
  if [ "${DOCK_BACKEND:-}" = plank ] && [ -f "$user_schemas/net.launchpad.plank.gschema.xml" ]; then
    export GSETTINGS_SCHEMA_DIR="$user_schemas"
  fi
}

# tx <src> <dst>: install a text asset through the palette/accent/radius transform (with backup)
tx() {
  local src="$1" dst="$2"
  backup "$dst"
  run mkdir -p "$(dirname "$dst")"
  if [ "$DRY_RUN" = 1 ]; then info "[dry-run] transform $src -> $dst"; return 0; fi
  python3 "$REPO_DIR/lib/theme.py" transform "$src" "$dst"
}

# Restart only the Golden Gate switcher; unrelated window switchers are untouched.
restart_switcher() {
  [ "${GG_NO_RESTART:-0}" = 1 ] && return 0
  [ "$DRY_RUN" = 1 ] && { info "[dry-run] restart Golden Gate switcher"; return 0; }
  local pid; pid="$(cat "$HOME/.cache/golden-gate-switcher.pid" 2>/dev/null || state_get SWITCHER_PID)"
  if [[ "$pid" =~ ^[0-9]+$ ]] && { [ "$(ps -p "$pid" -o comm= 2>/dev/null)" = alttab ] ||
       [[ "$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)" == *"$HOME/.local/lib/golden-gate/window_switcher.py"* ]]; }; then
    kill "$pid" 2>/dev/null || true
  fi
  if [ -x "$HOME/.local/bin/golden-gate-switcher" ]; then
    setsid nohup "$HOME/.local/bin/golden-gate-switcher" >/dev/null 2>&1 &
    state_set SWITCHER_PID "$!"
  fi
}
