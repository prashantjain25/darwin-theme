// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
import QtQuick
import org.kde.kirigami as Kirigami

// Original icon-only delegate: deliberately no button/panel hover artwork.
Item {
    id: icon
    required property var iconSource
    required property string label
    property real baseIconSize: 60
    property real zoomFactor: 1.55
    property real pointerX: -10000
    property real restingCenter: 0
    property bool pointerInside: false
    property bool running: false
    property bool active: false
    property bool grouped: false
    property bool attention: false
    property real gap: 10
    property real bottomInset: 11
    property real canvasHeight: baseIconSize * zoomFactor + bottomInset + 6
    property real dotInset: 3
    property bool showDots: false
    readonly property real influence: pointerInside ? Math.max(0, 1 - Math.abs(pointerX - restingCenter) / (baseIconSize * 2.1)) : 0
    readonly property real targetSize: baseIconSize * (1 + (zoomFactor - 1) * (1 - Math.cos(Math.PI * influence)) / 2)
    property real iconSize: targetSize
    signal activated(bool newInstance)
    width: visible ? iconSize + gap : 0
    height: canvasHeight
    activeFocusOnTab: visible
    Accessible.role: Accessible.Button
    Accessible.name: label
    Accessible.onPressAction: activated(false)
    Keys.onReturnPressed: activated(false)
    Keys.onSpacePressed: activated(false)
    Behavior on iconSize { NumberAnimation { duration: 135; easing.type: Easing.OutCubic } }

    Kirigami.Icon {
        id: artwork
        objectName: "artwork"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: icon.bottomInset
        width: icon.iconSize
        height: width
        source: icon.iconSource
        smooth: true
        roundToIconSize: false
        animated: false
        // Avoid KDE's selected/active icon treatment and hover frame.
        active: false
        opacity: hit.pressed ? 0.78 : 1
    }
    Row {
        objectName: "runningDot"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: icon.dotInset
        spacing: 3
        visible: icon.showDots && icon.running
        Repeater {
            model: icon.grouped ? 2 : 1
            Rectangle {
                width: 4; height: 4; radius: 2
                color: icon.attention ? "#ffbc57" : (icon.active ? "#f2f2f2" : "#a8a8ac")
            }
        }
    }
    MouseArea {
        id: hit
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        onClicked: mouse => icon.activated(mouse.button === Qt.MiddleButton || (mouse.modifiers & Qt.ShiftModifier) !== 0)
    }
}
