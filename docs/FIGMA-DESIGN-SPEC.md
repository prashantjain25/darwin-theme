# Figma design spec: values picked for the Linux desktop

Source: Figma file q76pEqJBDaoZkBTJj1tzwM, full JSON in `macos26.json` (33 MB),
condensed dump of all component pages in `summary_raw.txt`. Light mode unless noted.
Font in Figma: SF Pro 13 px, weight 510 (Medium). Your desktop uses Inter.

## Menus
- Menu padding: L12 T5 R12 B5. Row 24 px high, row width = menu width - 24, gap 8 (symbol/label/shortcut).
- Menu width 250 (Menu component) / 268 (Menubar example). Background corner radius **13**.
- Row hover/selected: radius **8**, fill = accent #0088ff, text white. Idle text #1a1a1a, shortcut text #bfbfbf, disabled #bfbfbf.
- Separator: 11 px tall, with a 1 px line #e6e6e6 (about 5 px above and below).
- Section header: 21 px, pad L18 T5 B4, SF Pro 10/700, color #727272.
- Menu background: Glass effect + fill #262626@100% + #f5f5f5@67%.
- Shadows: blur 25 black@16% + blur 2 black@10%.

## Liquid Glass materials
- Large/Medium, radius 34. Light: fill #262626 + #f5f5f5@67% (medium) / #fafafa@80% (large). Dark: #cccccc + #000000@67-85% + #ffffff@3%, layer opacity 67%.
- Shadow: y8 blur 40 black@12%. Glass layer tint #000000@20%.

## Windows
- Default window: radius **26**. Titlebar-only window: radius **16**. Utility panel: radius 15.
- Window shadow: y16 blur 48 black@35% + 1 px outline (spread 1) black@23%. Utility panel: y5 blur 20 black@30%.
- Standard title bar height **32**. Utility title bar 22.
- Window controls (standard): 14 px circles, gap 9, padding 1. Close #ff736a, Minimize #febc2e, Zoom #19c332. Inactive: black@15%. Stroke black@10% 0.5 px.
- Utility controls: 10 px, gap 7.

## Alerts
- 260 wide, radius **10**, padding L16 T20 R16 B16, gap 16. Side-by-side height 154, stacked 218.
- Shadow: y17 blur 45 black@50% + blur 1 black@20%.
- Buttons are pills (radius 100), 28 high. Primary #0088ff white text; Secondary #e6e6e6 text black@85%; Destructive #ff383c@23% with #ff383c text.

## Controls
- Push button: 24 high, radius **6**, padding L16 R16. Arrow button: 24 px circle.
- Text field / search field: 24 high, radius **6**, padding L8 R4. Search icon 16 px, gap 2.
- Switch: 54 x 24 pill, 2 px padding, knob 32 x 20 pill (idle white).
- Tooltip: radius 1, pad L6 T3 R6 B2, fill #f6f6f6@72% + background blur 20, shadow y1 blur 3 black@20%, text SF Pro 11 #4d4d4d.
- Popover: fill #ffffff@70% + #fafafa@20%, glass; shadows y4 blur 20 black@15% + blur 2.5 black@50%.
- Scrollbar: track 12 px wide, thumb 6 px.
- Sidebar row: 40 high (large), radius 8, selected fill black@11%, padding L8-10.
- Utility tab item: 29 high, radius 6, selected black@3%.

## Colors / text
- Accent blue #0088ff. Red #ff383c. Labels primary black@85%.
- Materials page has Ultrathin..Ultrathick (light and dark) fills.

# DARK MODE (light value -> dark value, from the Colors and Materials pages)
Dark mode is implemented in Figma through variable modes (not resolved in the file JSON); these pairs
come from the Colors page swatches and the `Mode=Dark` component variants.

## Text / labels
- Label primary: #000000@85% -> #ffffff@85%. Secondary: @50% -> @55%. Tertiary @25% -> @25%. Quaternary @10%. Quinary @5%.
- Solid text: primary #1a1a1a -> #f5f5f5; secondary #727272 -> #8a8a8a; tertiary #bfbfbf -> #404040; quaternary #d9d9d9 -> #262626; quinary #e6e6e6 -> #111111.

## Surface / background levels (dark)
- Primary #242424, Secondary #141414, Tertiary #0d0d0d, Quaternary #090909, Quinary #070707.
  (light equivalents: #d9d9d9, #d9d9d9, #f2f2f2, #f7f7f7, #fbfbfb, each with a black@10..2% overlay; dark uses white@10..2% overlays)
- This matches the "near black but slightly above" request: use #141414 for window decoration and #0d0d0d to #141414 for surfaces.

## Glass materials (dark)
- Large: fill #cccccc + #000000@85% + #ffffff@3%, layer opacity 67%. Medium: #cccccc + #000000@67% + #ffffff@3%, opacity 67%.
- Tint #000000@20% glass layer; shadow y8 blur 40 black@12%; radius 34 (large/medium), pill for small.

## Accent colors (light -> dark)
- Red #ff383c -> #ff4245; Orange #ff8d28 -> #ff9230; Yellow #ffcc00 -> #ffd600; Green #34c759 -> #30d158;
  Mint #00c8b3 -> #00dac3; Teal #00c3d0 -> #00d2e0; Cyan #00c0e8 -> #3cd3fe; **Blue #0088ff -> #0091ff**;
  Indigo #6155f5 -> #6d7cff; Purple #cb30e0 -> #db34f2; Pink #ff2d55 -> #ff375f; Brown #ac7f5e -> #b78a66; Gray #8e8e93 -> #98989f.

## Dark menu / controls (derived)
- Menu text #f5f5f5 / @85%, shortcut text white@55%, hover pill accent #0091ff with white text.
- Separators white@10%; control strokes white@10%.
- Also in the file: `Menu Bar and Dock` has `Color Mode=Dark` variants for menu bar items and dock app icons (Dark app icons).
