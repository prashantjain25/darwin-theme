// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    property var cfg_launchers: []
    property var cfg_utilityLaunchers: []
    property alias cfg_iconSize: iconSize.value
    property real cfg_zoomFactor: 1.55
    property alias cfg_showDownloads: downloads.checked
    property alias cfg_showTrash: trash.checked
    property alias cfg_showRunningDots: dots.checked
    spacing: 12
    Controls.Label { text: "Pinned application URLs (one per line, original order preserved):"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Controls.ScrollView {
        Layout.fillWidth: true
        Layout.preferredHeight: 180
        Controls.TextArea {
            text: page.cfg_launchers.join("\n")
            selectByMouse: true
            wrapMode: TextEdit.NoWrap
            onTextChanged: {
                const urls = text.split("\n").filter(url => url.length > 0);
                if (urls.join("\n") !== page.cfg_launchers.join("\n")) page.cfg_launchers = urls;
            }
        }
    }
    Controls.Label { text: "Supports applications:, preferred:, and file: URLs. No default replaces your existing pins."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    RowLayout {
        Controls.Label { text: "Icon size:" }
        Controls.SpinBox { id: iconSize; from: 24; to: 96; value: 60 }
        Controls.Label { text: "px (60 at 2560px / scale 1)" }
    }
    RowLayout {
        Controls.Label { text: "Magnification:" }
        Controls.Slider {
            from: 1; to: 2; stepSize: 0.05
            value: page.cfg_zoomFactor
            onMoved: page.cfg_zoomFactor = value
        }
        Controls.Label { text: page.cfg_zoomFactor.toFixed(2) + "×" }
    }
    Controls.CheckBox { id: downloads; text: "Show Downloads after separator" }
    Controls.CheckBox { id: dots; text: "Show running-application dots (off by default)" }
    Controls.CheckBox { id: trash; text: "Show Trash after separator"; checked: true }
    Controls.Label { text: "Utility launcher URLs (existing pins moved after separator, not duplicated):"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Controls.TextField {
        Layout.fillWidth: true
        text: page.cfg_utilityLaunchers.join(",")
        onEditingFinished: page.cfg_utilityLaunchers = text.split(",").filter(url => url.length > 0)
    }
    Controls.Label { text: "Panel height: at least ceil(icon size × magnification + 17). Use 112px for the defaults; disable the panel background. The painted glass remains compact."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Item { Layout.fillHeight: true }
}
