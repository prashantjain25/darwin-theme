// SPDX-License-Identifier: MIT
// Place only our Spotlight; Wayland clients cannot choose absolute screen positions.
(function () {
    function place(window) {
        var appId = String(window.desktopFileName || window.resourceClass || '');
        if (appId !== 'darwin-spotlight' && appId !== 'darwin-spotlight.desktop') return;
        if (!window.output || !window.output.geometry) return;
        var output = window.output.geometry;
        var frame = window.frameGeometry;
        window.frameGeometry = {
            x: output.x + Math.round((output.width - frame.width) / 2),
            y: output.y + Math.round(output.height * 0.22),
            width: frame.width,
            height: frame.height
        };
        window.keepAbove = true;
        window.skipTaskbar = true;
        window.skipPager = true;
        window.skipSwitcher = true;
    }
    workspace.windowAdded.connect(place);
})();
