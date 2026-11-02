# Darwin Dark Aurorae (MIT)

All SVG geometry is newly authored for this package. No Apple artwork, fonts,
or third-party theme artwork is included. System KDE files were read only to
learn the public FrameSvg element names.

Install this directory as `aurorae/themes/Darwin-Dark` in a KDE data root.
Select `org.kde.kwin.aurorae` with theme `__aurorae__svg__Darwin-Dark`.
KWin's global ButtonsOnLeft=XIA and ButtonsOnRight= must be set separately:
Aurorae's legacy LeftButtons is descriptive; Plasma 6 uses global options.
Use normal button size (ButtonSize=1 in auroraerc's Darwin-Dark group) and
BorderSize=Tiny to retain native 14px controls and the 1px frame. Large button
size or custom DPI settings can enlarge both controls and titlebar.

Native design: 32px titlebar, 14px circles, 9px gaps and vertical insets, 16px
left inset and upper corner radius. Active/inactive rim is 12%/6.5% white.
Maximized windows use square corners. Shadow padding is deliberately zero;
there is no baked-in drop shadow. Aurorae does not round a client's interior
or GTK/libadwaita client-side decorations; those are separate concerns.
