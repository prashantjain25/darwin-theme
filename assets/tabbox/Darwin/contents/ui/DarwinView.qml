/*
 * SPDX-FileCopyrightText: 2026 Darwin contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 */
pragma ComponentBehavior: Bound
import QtQuick
import org.kde.kirigami as Kirigami

// Visual-only component: the native TabBox model remains one row per window.
// Separating the view also permits a real offscreen Qt preview outside KWin.
Item {
    id: root
    objectName: "darwinOverlay"

    property var model
    property var applicationLabels: ({})
    property int currentIndex: 0
    property real screenWidth: 1920
    // Set by the installer from the theme mode (dark/light); light is the packaged default.
    property bool dark: false
    readonly property real maximumWidth: Math.max(1, screenWidth - 40)
    readonly property real padding: Math.min(20, maximumWidth / 4)
    readonly property real availableWidth: Math.max(0, maximumWidth - 2 * padding)
    readonly property real tileWidth: Math.min(108, Math.max(44, Math.floor(availableWidth / Math.max(1, icons.count))))
    readonly property real iconSize: Math.min(88, Math.max(0, tileWidth - 20))
    signal activated(int index)

    width: Math.min(maximumWidth, icons.count * tileWidth + 2 * padding)
    height: 148
    clip: true
    focus: true

    Rectangle {
        objectName: "glassBackground"
        anchors.fill: parent
        radius: 20
        color: root.dark ? Qt.rgba(30 / 255, 30 / 255, 32 / 255, 0.78) : Qt.rgba(222 / 255, 222 / 255, 222 / 255, 0.67)
        border.width: root.dark ? 1 : 0
        border.color: "#2effffff"
        antialiasing: true
    }

    ListView {
        id: icons
        objectName: "windowList"
        x: root.padding
        y: 0
        width: Math.max(0, root.width - 2 * root.padding)
        height: 128
        orientation: ListView.Horizontal
        layoutDirection: Qt.LeftToRight
        model: root.model
        currentIndex: root.currentIndex
        clip: true
        interactive: false
        keyNavigationEnabled: false
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 0
        highlightResizeDuration: 0
        // No style-provided highlight: it would introduce the Breeze blue pill.
        highlight: null

        function keepCurrentVisible() {
            if (currentIndex >= 0 && currentIndex < count) {
                positionViewAtIndex(currentIndex, ListView.Contain);
            }
        }
        onCurrentIndexChanged: Qt.callLater(keepCurrentVisible)
        onWidthChanged: Qt.callLater(keepCurrentVisible)
        onCountChanged: Qt.callLater(keepCurrentVisible)

        delegate: WindowTile { }
        component WindowTile: Item {
            id: tile
            required property int index
            required property var model
            readonly property string appLabel: root.applicationLabels[String(model.windowId)] || "Application"
            readonly property bool selected: index === icons.currentIndex
            width: root.tileWidth
            height: 128
            Accessible.name: appLabel
            Accessible.role: Accessible.ListItem

            Rectangle {
                x: 0
                y: 20
                width: parent.width
                height: 108
                radius: 7
                color: root.dark ? "#33ffffff" : "#28000000"
                visible: tile.selected
                antialiasing: true
            }
            Kirigami.Icon {
                x: (parent.width - width) / 2
                y: 30 + (88 - height) / 2
                width: root.iconSize
                height: root.iconSize
                source: tile.model.icon
                // Never recolor/tint the window's actual application icon.
                active: false
                smooth: true
            }
            TapHandler {
                onSingleTapped: {
                    if (tile.selected) {
                        root.activated(tile.index);
                    } else {
                        root.currentIndex = tile.index;
                    }
                }
                onDoubleTapped: root.activated(tile.index)
            }
        }
    }

    // This is attached to the *selected icon's x*, not a dialog-wide footer.
    // Outside the clipped strip so the original tile+20 label width is retained.
    Text {
        objectName: "selectedApplicationLabel"
        x: Math.max(0, Math.min(root.width - width,
            root.padding + (icons.currentItem ? icons.currentItem.x : 0) - icons.contentX - 10))
        y: 129
        width: Math.min(root.width, root.tileWidth + 20)
        height: 18
        visible: icons.currentItem !== null
        text: (icons.currentItem as WindowTile)?.appLabel ?? ""
        color: root.dark ? "#f5f5f5" : "#1a1a1a"
        font.pointSize: 10
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        textFormat: Text.PlainText
        maximumLineCount: 1
    }

    Keys.onPressed: event => {
        if (icons.count > 0 && (event.key === Qt.Key_Left || event.key === Qt.Key_Right)) {
            const step = event.key === Qt.Key_Right ? 1 : -1;
            root.currentIndex = (root.currentIndex + step + icons.count) % icons.count;
            event.accepted = true;
        } else {
            event.accepted = false;
        }
    }
}
