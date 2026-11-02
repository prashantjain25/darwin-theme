// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: applet
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    preferredRepresentation: fullRepresentation
    switchWidth: 0
    switchHeight: 0
    Layout.minimumWidth: applet.fullRepresentationItem?.implicitWidth ?? 200
    Layout.preferredWidth: applet.fullRepresentationItem?.implicitWidth ?? 200
    Layout.maximumWidth: applet.fullRepresentationItem?.implicitWidth ?? 200
    Layout.minimumHeight: applet.fullRepresentationItem?.implicitHeight ?? 112
    Layout.preferredHeight: applet.fullRepresentationItem?.implicitHeight ?? 112
    fullRepresentation: Dock {
        id: dock
        launchers: Plasmoid.configuration.launchers
        utilityLaunchers: Plasmoid.configuration.utilityLaunchers
        baseIconSize: Plasmoid.configuration.iconSize
        zoomFactor: Plasmoid.configuration.zoomFactor
        showDownloads: Plasmoid.configuration.showDownloads
        showTrash: Plasmoid.configuration.showTrash
        showRunningDots: Plasmoid.configuration.showRunningDots
    }
}
