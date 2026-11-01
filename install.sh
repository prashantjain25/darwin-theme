#!/usr/bin/env bash
# Golden Gate LXQt Theme: desktop settings (Qt/Kvantum, GTK, Openbox, LXQt, picom, fonts, Lapce).
# The menu bar and dock are a separate element: see ./dock.sh
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

ALL_MODULES="fonts fontconfig kvantum gtk openbox lxqt picom pcmanfm lapce"
ONLY=""; SKIP=""; CONFIGURE=0; NO_RESTART=0; PCMANFM_DETAILED=0

usage() {
  cat <<EOF
Usage: ./install.sh [options]

Applies the Golden Gate desktop look. Every file it replaces is backed up
(restore with ./restore.sh). Settings live in config/theme.json.

Options:
  --configure         interactive wizard: mode, accent, window border, radius, menu rim, fonts
  --only a,b,c        run only these modules   (${ALL_MODULES// /,})
  --skip a,b          skip these modules
  --install-deps      apt-install missing packages and fetch the WhiteSur GTK/icon themes
  --pcmanfm-detailed  also switch PCManFM-Qt to the detailed list view
  --no-restart        do not restart picom / panel / openbox
  --dry-run           print what would happen, change nothing
  -y, --yes           do not ask questions
  -h, --help
EOF
}

while [ $# -gt 0 ]; do
  if parse_common_flag "$1"; then shift; continue; fi
  case "$1" in
    --configure) CONFIGURE=1;;
    --only) ONLY="${2//,/ }"; shift;;
    --skip) SKIP="${2//,/ }"; shift;;
    --pcmanfm-detailed) PCMANFM_DETAILED=1;;
    --no-restart) NO_RESTART=1;;
    -h|--help) usage; exit 0;;
    *) usage; die "unknown option: $1";;
  esac; shift
done

want() { # want <module>
  local m="$1"
  [ -n "$ONLY" ] && { [[ " $ONLY " == *" $m "* ]]; return; }
  [[ " $SKIP " != *" $m "* ]]
}

[ "$CONFIGURE" = 1 ] && python3 "$REPO_DIR/lib/theme.py" configure
load_theme_config
[ "$DRY_RUN" = 1 ] && warn "dry-run: nothing will be changed"
mkdir -p "$STATE_DIR" 2>/dev/null || true

# ================================================================ dependencies
check_deps() {
  step "Checking dependencies"
  local c
  for c in python3 curl unzip git fc-cache fc-list openbox picom lxqt-panel pcmanfm-qt kvantummanager \
           gresource glib-compile-resources gtk-update-icon-cache gsettings xprop; do need_cmd "$c"; done
  qt_style_plugins
  need_path "LXQt theme 'sombre-et-rond'" "install lxqt-themes (apt install lxqt-themes)" /usr/share/lxqt/themes/sombre-et-rond || MISSING_PKGS+=(lxqt-themes)
  local fams; fams="$(fc-list : family 2>/dev/null || true)"
  if grep -qiE '(^|,)Inter(,|$)' <<<"$fams"; then info "ok       font Inter"
  else info "missing  font Inter -> the bundled copy (SIL OFL 1.1) will be installed for you"; fi
  have lapce || [ -x "$HOME/opt/lapce/lapce" ] && info "ok       lapce (optional)" || info "optional lapce (not found, Lapce settings skipped)"
  ensure_whitesur_gtk "$GTK_SOURCE" || true
  ensure_whitesur_icons || true
  finish_deps
}

# ================================================================ modules
install_inter() {
  local fams; fams="$(fc-list : family 2>/dev/null || true)"
  if grep -qiE '(^|,)Inter(,|$)' <<<"$fams"; then info "Inter already installed"; return 0; fi
  local dst="$HOME/.local/share/fonts/Inter" f
  info "installing the bundled Inter (SIL OFL 1.1, (c) The Inter Project Authors) -> $dst"
  backup "$dst"; run mkdir -p "$dst"
  for f in "$REPO_DIR"/assets/fonts/Inter/*; do run cp -a "$f" "$dst/"; done   # includes OFL.txt as the license requires
  run fc-cache -f "$HOME/.local/share/fonts" >/dev/null 2>&1 || true
}

mod_fonts() {
  step "Fonts"
  [ "$FONT_UI" = "Inter" ] && install_inter
  if [ "$FONT_MONO" != "Maple Mono NF" ]; then info "mono font is '$FONT_MONO' (must already be installed)"; return 0; fi
  if [ -n "$(fc-list : family | grep -i "Maple Mono NF" | head -1)" ]; then info "Maple Mono NF already installed"; return 0; fi
  local url="https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMono-NF.zip"
  local sha="59098b87c895d871635d37680e88000ae2b2b25b55428195b228ec589e35fb89"
  local t; t="$(mktemp -d)"
  info "downloading Maple Mono NF v7.9 (20 MB)"
  run curl -fsSL -o "$t/nf.zip" "$url"
  if [ "$DRY_RUN" = 0 ]; then
    echo "$sha  $t/nf.zip" | sha256sum -c - >/dev/null || die "Maple Mono checksum mismatch"
    mkdir -p "$HOME/.local/share/fonts/MapleMono-NF"
    unzip -qo "$t/nf.zip" '*.ttf' -d "$HOME/.local/share/fonts/MapleMono-NF"
    fc-cache -f "$HOME/.local/share/fonts" >/dev/null 2>&1 || true
  fi
  rm -rf "$t"
}

mod_fontconfig() {
  step "fontconfig (monospace alias -> $FONT_MONO)"
  local dst="$HOME/.config/fontconfig/fonts.conf" tmp; tmp="$(mktemp)"
  sed "s|Maple Mono NF|$FONT_MONO|g" "$REPO_DIR/assets/fontconfig/fonts.conf" > "$tmp"
  install_file "$tmp" "$dst"; rm -f "$tmp"
  run fc-cache -f >/dev/null 2>&1 || true
}

mod_kvantum() {
  step "Kvantum (Qt apps, PCManFM-Qt inner views, menus)"
  local d="$HOME/.config/Kvantum/WhiteSurDark"
  tx "$REPO_DIR/assets/kvantum/WhiteSurDark/WhiteSurDark.kvconfig" "$d/WhiteSurDark.kvconfig"
  tx "$REPO_DIR/assets/kvantum/WhiteSurDark/WhiteSurDark.svg"      "$d/WhiteSurDark.svg"
  backup "$HOME/.config/Kvantum/kvantum.kvconfig"
  run python3 "$REPO_DIR/lib/ini.py" "$HOME/.config/Kvantum/kvantum.kvconfig" General theme=WhiteSurDark
  info "PCManFM-Qt: the 'transparent_pcmanfm_*' hacks, striped rows, dimmed header and dark toolbar field are part of this theme."
}

build_gtk_dark() {
  local src dst tmp v r
  src="$(whitesur_gtk_dir "$GTK_SOURCE")" || { warn "WhiteSur-Dark GTK theme not found; skipping GTK theme build"; return 0; }
  dst="$HOME/.themes/WhiteSur-Dark-Black"
  info "building $dst from $src (darker palette, accent $ACCENT)"
  [ "$DRY_RUN" = 1 ] && return 0
  backup "$dst"
  rm -rf "$dst"; mkdir -p "$HOME/.themes"; cp -r "$src" "$dst"
  sed -i 's/^Name=.*/Name=WhiteSur-Dark-Black/' "$dst/index.theme" 2>/dev/null || true
  tmp="$(mktemp -d)"
  for v in gtk-3.0 gtk-4.0; do
    local g="$src/$v/gtk.gresource"; [ -f "$g" ] || continue
    mkdir -p "$tmp/$v"; ( cd "$tmp/$v"
      for r in $(gresource list "$g"); do mkdir -p ".$(dirname "$r")"; gresource extract "$g" "$r" > ".$r"; done
      find . -name '*.css' -exec python3 "$REPO_DIR/lib/gtkdark.py" {} + >/dev/null
      [ "$ACCENT" != "#0091ff" ] && find . -name '*.css' -exec sed -i "s/#0091ff/$ACCENT/gI" {} +
      { echo '<?xml version="1.0" encoding="UTF-8"?><gresources><gresource prefix="/">'
        for r in $(gresource list "$g"); do echo "<file>${r#/}</file>"; done
        echo '</gresource></gresources>'; } > res.xml
      glib-compile-resources --sourcedir=. --target="$dst/$v/gtk.gresource" res.xml )
  done
  rm -rf "$tmp"
}

install_css_block() { # install_css_block <dst css>
  local dst="$1" tmp; tmp="$(mktemp)"
  python3 "$REPO_DIR/lib/theme.py" transform "$REPO_DIR/assets/gtk/gtk.css" "$tmp"
  backup "$dst"
  [ "$DRY_RUN" = 1 ] && { info "[dry-run] css block -> $dst"; rm -f "$tmp"; return 0; }
  mkdir -p "$(dirname "$dst")"; touch "$dst"
  sed -i '/^\/\* BEGIN golden-gate-lxqt-theme \*\//,/^\/\* END golden-gate-lxqt-theme \*\//d' "$dst"
  { echo "/* BEGIN golden-gate-lxqt-theme */"; cat "$tmp"; echo "/* END golden-gate-lxqt-theme */"; } >> "$dst"
  rm -f "$tmp"
}

mod_gtk() {
  step "GTK (theme, menus, fonts)"
  local theme="$GTK_SOURCE"
  if [ "$MODE" = dark ]; then build_gtk_dark; theme="WhiteSur-Dark-Black"; fi
  install_css_block "$HOME/.config/gtk-3.0/gtk.css"
  install_css_block "$HOME/.config/gtk-4.0/gtk.css"
  local prefer=true; [ "$MODE" = light ] && prefer=false
  local f
  for f in "$HOME/.config/gtk-3.0/settings.ini" "$HOME/.config/gtk-4.0/settings.ini"; do
    backup "$f"
    run python3 "$REPO_DIR/lib/ini.py" "$f" Settings "gtk-theme-name=$theme" "gtk-icon-theme-name=$ICON_THEME" \
        "gtk-font-name=$FONT_UI $FONT_SIZE" "gtk-application-prefer-dark-theme=$prefer"
  done
  backup "$HOME/.gtkrc-2.0"
  if [ "$DRY_RUN" = 0 ]; then
    touch "$HOME/.gtkrc-2.0"
    sed -i '/^gtk-theme-name=/d; /^gtk-icon-theme-name=/d; /^gtk-font-name=/d' "$HOME/.gtkrc-2.0"
    printf 'gtk-theme-name="%s"\ngtk-icon-theme-name="%s"\ngtk-font-name="%s %s"\n' "$theme" "$ICON_THEME" "$FONT_UI" "$FONT_SIZE" >> "$HOME/.gtkrc-2.0"
  fi
  if have gsettings && [ "${GG_SKIP_GSETTINGS:-0}" != 1 ]; then
    local scheme=prefer-dark; [ "$MODE" = light ] && scheme=default
    run gsettings set org.gnome.desktop.interface gtk-theme "$theme" || true
    run gsettings set org.gnome.desktop.interface icon-theme "$ICON_THEME" || true
    run gsettings set org.gnome.desktop.interface font-name "$FONT_UI $FONT_SIZE" || true
    run gsettings set org.gnome.desktop.interface monospace-font-name "$FONT_MONO $FONT_SIZE" || true
    run gsettings set org.gnome.desktop.interface color-scheme "$scheme" || true
  fi
}

mod_openbox() {
  step "Openbox (window decoration, border, traffic lights)"
  local d="$HOME/.themes/OpenboxSur-Dark-Custom/openbox-3" a="$REPO_DIR/assets/openbox/OpenboxSur-Dark-Custom/openbox-3" f
  backup "$HOME/.themes/OpenboxSur-Dark-Custom"
  run mkdir -p "$d"
  for f in "$a"/*.xbm; do run cp -a "$f" "$d/"; done
  if [ "$DRY_RUN" = 0 ]; then
    python3 "$REPO_DIR/lib/theme.py" transform "$a/themerc" "$d/themerc"
    python3 "$REPO_DIR/lib/theme.py" openbox-border "$d/themerc"
    # geometry that makes the traffic lights land on Figma's x=9/32/55 (see docs/)
    sed -i -E "s/^padding.width:.*/padding.width: 8/; s/^padding.height:.*/padding.height: 8/" "$d/themerc"
    [ "$BORDER_WIDTH" = 0 ] && sed -i -E "s/^padding.height:.*/padding.height: 8/" "$d/themerc"
  fi
  local rc found=0
  for rc in "$HOME/.config/openbox/rc.xml" "$HOME/.config/openbox/lxqt-rc.xml"; do
    [ -f "$rc" ] || continue; found=1
    backup "$rc"; run python3 "$REPO_DIR/lib/openbox_rc.py" "$rc" OpenboxSur-Dark-Custom "$TB_FONT" "$FONT_UI" "$SWITCHER_DIALOG"
  done
  [ "$found" = 1 ] || warn "no ~/.config/openbox/rc.xml found; select 'OpenboxSur-Dark-Custom' in LXQt Appearance > Openbox"
}

mod_lxqt() {
  step "LXQt (theme 'sombre-et-rond', icon theme, fonts, panel stylesheet)"
  local td="$HOME/.local/share/lxqt/themes/sombre-et-rond"
  if [ ! -d "$td" ]; then
    backup "$td"; run mkdir -p "$(dirname "$td")"; run cp -r /usr/share/lxqt/themes/sombre-et-rond "$td"
  fi
  compose_panel_qss
  local lc="$HOME/.config/lxqt/lxqt.conf"; backup "$lc"
  run python3 "$REPO_DIR/lib/ini.py" "$lc" General "theme=sombre-et-rond" "icon_theme=$ICON_THEME" \
      "font=\"$FONT_UI,$FONT_SIZE,-1,5,50,0,0,0,0,0\""
  run python3 "$REPO_DIR/lib/ini.py" "$lc" Appearance "icon_theme=$ICON_THEME" "widget_style=kvantum"
  run python3 "$REPO_DIR/lib/ini.py" "$lc" Qt "style=kvantum" \
      "font=\"$FONT_UI,$FONT_SIZE,-1,5,400,0,0,0,0,0,0,0,0,0,0,1\""
}

mod_picom() {
  step "picom (rounded corners, shadows, blur)"
  render "$REPO_DIR/assets/picom/picom.conf.in" "$HOME/.config/picom.conf"
}

mod_pcmanfm() {
  step "PCManFM-Qt (view: $FM_VIEW)"
  info "Styling comes from the Kvantum module (list stripes, header, sidebar, location bar)."
  local f="$HOME/.config/pcmanfm-qt/lxqt/settings.conf"
  backup "$f"
  run python3 "$REPO_DIR/lib/ini.py" "$f" FolderView "Mode=$FM_VIEW" "ShowHidden=false"
  run python3 "$REPO_DIR/lib/ini.py" "$f" Window "SidePaneMode=places" "SidePaneVisible=true"   # Places list, not the directory tree
  warn "close the PCManFM-Qt windows to apply (log out for the desktop icons)"
}

mod_lapce() {
  step "Lapce"
  local bin; bin="$(command -v lapce || true)"; [ -z "$bin" ] && [ -x "$HOME/opt/lapce/lapce" ] && bin="$HOME/opt/lapce/lapce"
  [ -n "$bin" ] || { info "Lapce not found, skipping"; return 0; }
  local px=$(( FONT_SIZE * 4 / 3 )) dst="$HOME/.config/lapce-stable/settings.toml" tmp; tmp="$(mktemp)"
  sed -e "s|Maple Mono NF|$FONT_MONO|g" -e "s|^font-family = \"Inter\"|font-family = \"$FONT_UI\"|" \
      -e "s|^font-size = 15|font-size = $px|" "$REPO_DIR/assets/lapce/settings.toml" > "$tmp"
  install_file "$tmp" "$dst"; rm -f "$tmp"
  # winit derives a ~1.6x scale from high-DPI panels; force 1.0 so Lapce's 'scale = 1.0' means 1.0
  local w="$HOME/.local/bin/lapce-1x"; backup "$w"
  if [ "$DRY_RUN" = 0 ]; then
    mkdir -p "$HOME/.local/bin"
    printf '#!/bin/sh\nexport WINIT_X11_SCALE_FACTOR=1\nexec "%s" "$@"\n' "$bin" > "$w"; chmod +x "$w"
  fi
  info "start Lapce with ~/.local/bin/lapce-1x (forces a true 1.0 UI scale)"
}

# ================================================================ run
check_deps
state_set MODE "$MODE"
for m in $ALL_MODULES; do want "$m" && "mod_$m"; done

if [ "$NO_RESTART" = 0 ]; then
  step "Reloading the session pieces"
  reconfigure_openbox
  want picom && restart_picom
  want lxqt && restart_panel
fi

step "Done"
info "Backups: $BACKUP_DIR   (undo with ./restore.sh)"
info "Log out and back in (or restart Qt/GTK apps) to see everything."
info "Next: ./dock.sh installs the menu bar and dock."
