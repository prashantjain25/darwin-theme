// Plasma 6 scripting API; use existing primary-screen panels and preserve extras.
// Native Plasma dock works on Wayland: no Plank, Latte, picom or X11 helpers.
(function () {
    function findPanel(edge) {
        var existing = panels();
        for (var i = 0; i < existing.length; i++) {
            if (existing[i].location === edge && existing[i].screen === 0) return existing[i];
        }
        var p = new Panel();
        p.screen = 0;
        p.location = edge;
        return p;
    }
    function ensure(p, type) {
        var ws = p.widgets();
        for (var i = 0; i < ws.length; i++) if (ws[i].type === type) return ws[i];
        return p.addWidget(type);
    }
    var options = typeof DARWIN_OPTIONS === 'undefined' ? {} : DARWIN_OPTIONS;
    var top;
    if (options.menubar !== false) {
    top = findPanel('top');
    top.height = options.barHeight || 34;
    top.floating = true;   // spans the full width (the theme removes the gap) so its bottom corners can be rounded
    top.alignment = 'center';
    top.lengthMode = 'fill';
    top.hiding = 'none';
    var launcher = ensure(top, 'org.kde.plasma.kickoff');
    if (options.startIcon) {
        // The launcher is always the Apple glyph from WhiteSur, whatever icon theme is active.
        launcher.currentConfigGroup = ['General'];
        launcher.writeConfig('icon', options.startIcon);
    }
    ensure(top, 'org.kde.plasma.appmenu');
    ensure(top, 'org.kde.plasma.panelspacer');
    ensure(top, 'org.kde.plasma.systemtray');
    var clock = ensure(top, 'org.kde.plasma.digitalclock');
    clock.currentConfigGroup = ['Appearance'];
    clock.writeConfig('showDate', true);
    clock.writeConfig('dateFormat', 'custom');
    clock.writeConfig('customDateFormat', 'ddd MMM d');
    clock.writeConfig('use24hFormat', 0);
    clock.writeConfig('fontFamily', options.font || 'Inter');
    clock.writeConfig('autoFontAndSize', false);
    clock.writeConfig('fontSize', 10);
    clock.writeConfig('fontWeight', 600);
    clock.writeConfig('fontStyleName', 'SemiBold');
    clock.writeConfig('dateDisplayFormat', 'BesideTime');
    }
    var dock;
    if (options.dock !== false) {
    dock = findPanel('bottom');
    dock.floating = true;
    dock.alignment = 'center';
    dock.lengthMode = 'fit';
    dock.hiding = options.hiding || 'dodgewindows';
    if (options.dockWidget) {
        dock.height = options.dockHeight || 112;
        var mine = null, stock = null, ws = dock.widgets();
        for (var i = 0; i < ws.length; i++) {
            if (ws[i].type === options.dockWidget) mine = ws[i];
            else if (ws[i].type === 'org.kde.plasma.icontasks' || ws[i].type === 'org.kde.plasma.taskmanager'
                     || ws[i].type === 'com.prashantjain25.goldengate.dock'
                     || ws[i].type === 'com.prashantjain25.darwinosx.dock') stock = ws[i];   // the last one is the dock under its former name
        }
        if (!mine) {
            mine = dock.addWidget(options.dockWidget);
            mine.currentConfigGroup = ['General'];
            if (stock) {
                // Copy the whole original pin list before removing the stock widget.
                stock.currentConfigGroup = ['General'];
                var pins = stock.readConfig('launchers');
                if (pins && pins.length) mine.writeConfig('launchers', pins);
            }
            mine.writeConfig('iconSize', options.dockIcon || 60);
            mine.writeConfig('zoomFactor', 1.55);
            mine.writeConfig('showTrash', true);
            mine.reloadConfig();
            if (stock) stock.remove();
        }
    } else {
        dock.height = 64;
        var task = ensure(dock, 'org.kde.plasma.icontasks');
        task.currentConfigGroup = ['General'];
        // Do not overwrite launchers. KDE initializes sensible defaults on fresh panels.
    }
    }
    print('DARWIN_LAYOUT_OK top=' + (top ? top.id : 'unchanged') + ' dock=' + (dock ? dock.id : 'unchanged'));
})();
