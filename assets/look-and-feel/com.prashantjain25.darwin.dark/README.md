# Darwin Dark global theme (MIT)

ID: `com.prashantjain25.darwin.dark`. These defaults reference the
separately installed Darwin-Dark Aurorae and Plasma packages and the
DarwinDark color scheme. Install those together before selecting it.

KDE's installed Breeze widget style, breeze-dark icons and breeze_cursors
are external runtime dependencies, not redistributed artwork. No Apple
artwork or fonts are shipped. Wallpaper, splash and screen-lock appearance
are intentionally not overridden. This package intentionally contains no
panel layout script; the unified installer's optional layout owns that.

Some Plasma versions only honor a subset of global-theme KConfig defaults.
The installer must explicitly set KWin's ButtonsOnLeft=XIA, empty
ButtonsOnRight, BorderSize=Tiny, BorderSizeAuto=false and the normal Aurorae
ButtonSize=1 to guarantee 32px/14px native geometry. All sizes are logical
pixels at 96 DPI; custom DPI and user-selected larger buttons can enlarge it.
