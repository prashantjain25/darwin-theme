/*
 * Native switcher lifecycle adapted from KDE's big_icons main.qml.
 * SPDX-FileCopyrightText: 2011 Martin Gräßlin <mgraesslin@kde.org>
 * SPDX-FileCopyrightText: 2026 Darwin contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 */
pragma ComponentBehavior: Bound
import QtQuick
import org.kde.plasma.core as PlasmaCore
import org.kde.kwin as KWin

KWin.TabBoxSwitcher {
    id: tabBox

    currentIndex: (instantiator.object as DarwinDialog)?.currentIndex ?? currentIndex

    // ClientModel exposes windowId/icon/caption but no application-name role.
    // Resolve that UUID against KWin's Wayland-safe Window objects; never use a
    // document's caption as the app label and never group/dedupe the model.
    function applicationLabels() {
        const labels = {};
        const aliases = {
            "google-chrome": "Google Chrome", "google-chrome-stable": "Google Chrome",
            "pcmanfm-qt": "Files", "qterminal": "Terminal",
            "jetbrains-idea": "IntelliJ IDEA", "org.kde.dolphin": "Dolphin",
            "org.kde.konsole": "Konsole", "org.kde.kate": "Kate"
        };
        for (const window of KWin.Workspace.windows) {
            const raw = String(window.resourceClass || window.resourceName || window.desktopFileName || "Application");
            const shortName = raw.replace(/\.desktop$/i, "").split(".").pop();
            labels[String(window.internalId)] = aliases[raw.toLowerCase()]
                || shortName.charAt(0).toUpperCase() + shortName.slice(1);
        }
        return labels;
    }

    // KWin owns Alt+Tab / Shift+Alt+Tab, Alt-release and Escape. Never grab keys.
    Instantiator {
        id: instantiator
        active: tabBox.visible
        delegate: DarwinDialog { }
    }

    component DarwinDialog: PlasmaCore.Dialog {
        property alias currentIndex: overlay.currentIndex
        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Types.NoBackground
        visible: tabBox.visible
        flags: Qt.Popup | Qt.FramelessWindowHint
        color: "transparent"
        x: tabBox.screenGeometry.x + (tabBox.screenGeometry.width - overlay.width) / 2
        y: tabBox.screenGeometry.y + (tabBox.screenGeometry.height - overlay.height) / 2

        mainItem: DarwinView {
            id: overlay
            currentIndex: tabBox.currentIndex
            model: tabBox.model
            applicationLabels: tabBox.applicationLabels()
            screenWidth: tabBox.screenGeometry.width
            onActivated: index => tabBox.model.activate(index)
            Connections {
                target: tabBox
                function onCurrentIndexChanged() { overlay.currentIndex = tabBox.currentIndex; }
            }
            Connections {
                target: tabBox.model
                function onModelReset() { overlay.applicationLabels = tabBox.applicationLabels(); }
            }
        }

        onSceneGraphError: () => {
            // Avoid QtQuick's default fatal handler on a graphics reset (as upstream).
        }
    }
}
