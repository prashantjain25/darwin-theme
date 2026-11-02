# Darwin Dark Plasma desktop theme (MIT)

All SVGs are new geometric artwork. No third-party themes, Apple artwork,
fonts or icons have been copied. KDE metadata and nine-slice element names
are interface contracts, not copied artwork.

Install as `plasma/desktoptheme/Darwin-Dark` under a KDE data root.
The primary panel is #141414 at 84% opacity with a 13% white rim. Plasma's
full-width top panel disables outer borders when flush with screen edges.
A floating icons-only panel uses the same native 16px corners; floating
margins are 8px. The `floating` prefix supplies Plasma 6's margin metrics;
Panel.qml uses the unprefixed artwork for actual floating panel rendering.
`thick` defines compact applet padding; mask tiles keep blur round. A separate
original gradient shadow supplies a small falloff. Solid and opaque copies
preserve the same shape without translucency for those panel modes.

Missing widgets intentionally inherit KDE's installed `default` (Breeze)
image set. FallbackTheme documents this; current KSvg also enforces `default`
as its built-in fallback. A local `colors` file fixes the charcoal palette.
KDE Breeze remains separately licensed and is not bundled here.

This package does not create panels, select wallpaper, or force blur. A
layout/installer must create a top panel and floating icons-only dock and
select translucency. Blur also needs KWin's blur effect enabled. Panel radius
may be disabled at touching screen edges by Plasma, as intended.
