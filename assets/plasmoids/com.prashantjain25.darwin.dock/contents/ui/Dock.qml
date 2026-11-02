// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects
import org.kde.taskmanager as TaskManager
import QtCore

Item {
    id: root
    objectName: "darwinDock"
    // The shell/installer supplies these verbatim, including preferred:/file: URLs.
    property list<string> launchers: []
    property list<string> utilityLaunchers: ["applications:systemsettings.desktop"]
    property real baseIconSize: 60
    property real zoomFactor: 1.55
    property bool showDownloads: false
    property bool showTrash: true
    // Off by default: the running-app dots do not reproduce the macOS dock exactly.
    property bool showRunningDots: false
    // Every spacing follows the Figma dock (62 px glass, 36 px icons, 9 px gap, 8 px side padding,
    // 10 px top padding), scaled by the icon size, so nothing is hand-tuned per screen.
    readonly property real unit: baseIconSize / 36
    readonly property real gap: Math.round(9 * unit)
    readonly property real padding: Math.round(8 * unit)
    readonly property real idleHeight: Math.round(62 * unit)
    readonly property real iconBottomInset: idleHeight - Math.round(10 * unit) - baseIconSize   // icon top padding = 10u
    readonly property real dotInset: Math.round(5 * unit)
    readonly property real separatorWidth: gap + 1
    readonly property real radiusPx: Math.round(idleHeight * 0.28)
    readonly property real canvasHeight: Math.ceil(idleHeight + baseIconSize * (zoomFactor - 1) + 6)
    readonly property alias tasksModel: tasks
    readonly property int taskCount: tasks.count
    readonly property real baseRowWidth: tasks.count * (baseIconSize + gap) + (showDownloads ? baseIconSize + gap : 0) + (showTrash ? baseIconSize + gap : 0) + (hasUtilities ? separatorWidth : 0)
    // Rows are ordered here, not by TasksModel.move(), which does not reliably reorder a mix of pinned
    // apps and running windows. Pinned apps keep the supplied order; other windows follow in model order.
    property int revision: 0
    function role(row: int, id: int): var {
        revision;   // dependency: re-evaluate when the model changes
        return tasks.data(tasks.makeModelIndex(row), id);
    }
    function desktopName(url: string): string {
        const clean = String(url).split("?")[0];
        const match = clean.match(/([^\/:]+\.desktop)$/);
        return match ? match[1].toLowerCase() : clean.toLowerCase();
    }
    function pinRank(url: string): int {
        const position = tasks.launcherPosition(url);
        if (position >= 0) return position;
        const wanted = desktopName(url);
        for (let i = 0; i < launchers.length; ++i) {
            if (desktopName(launchers[i]) === wanted) return i;
        }
        return 100000;
    }
    function sortedRows(utility: bool): var {
        revision;
        const rows = [];
        for (let row = 0; row < tasks.count; ++row) {
            const url = String(tasks.data(tasks.makeModelIndex(row), TaskManager.AbstractTasksModel.LauncherUrlWithoutIcon));
            if (isUtility(url) === utility) rows.push({ row: row, rank: pinRank(url) });
        }
        rows.sort((x, y) => (x.rank - y.rank) || (x.row - y.row));
        return rows.map(item => item.row);
    }
    readonly property var appRows: sortedRows(false)
    readonly property var utilityRows: sortedRows(true)
    readonly property int utilityCount: utilityRows.length
    readonly property bool hasUtilities: showDownloads || showTrash || utilityCount > 0
    // Extra transparent horizontal room is reserved, never painted as padding.
    // Keep the panel 112 px high for 60px icons; do not resize its Wayland window
    // on hover (that clips icons and makes auto-hide flicker).
    implicitWidth: baseRowWidth + padding * 2 + baseIconSize * (zoomFactor - 1) * 3
    implicitHeight: canvasHeight
    property real pointerX: hover.point.position.x
    readonly property bool pointerInside: hover.hovered

    function isUtility(url: string): bool {
        for (const launcher of utilityLaunchers) {
            if (url === launcher) return true;
        }
        return false;
    }

    // Decide from current model roles, not cached window IDs. Group parents
    // activate a real child, cycling on repeated clicks rather than doing nothing.
    function activateTask(row: int, newInstance: bool): void {
        const idx = tasks.makeModelIndex(row);
        const isLauncher = Boolean(tasks.data(idx, TaskManager.AbstractTasksModel.IsLauncher));
        if (isLauncher || newInstance) {
            tasks.requestNewInstance(idx);
            return;
        }
        if (Boolean(tasks.data(idx, TaskManager.AbstractTasksModel.IsGroupParent))) {
            const count = tasks.rowCount(idx);
            let next = 0;
            for (let c = 0; c < count; ++c) {
                if (Boolean(tasks.data(tasks.makeModelIndex(row, c), TaskManager.AbstractTasksModel.IsActive))) next = (c + 1) % count;
            }
            tasks.requestActivate(tasks.makeModelIndex(row, next));
        } else if (Boolean(tasks.data(idx, TaskManager.AbstractTasksModel.IsActive)) && !Boolean(tasks.data(idx, TaskManager.AbstractTasksModel.IsMinimized))) {
            tasks.requestToggleMinimized(idx);
        } else {
            tasks.requestActivate(idx);
        }
    }

    function centerFor(ordinal: int, utility: bool): real {
        return (width - baseRowWidth) / 2 + (ordinal + 0.5) * (baseIconSize + gap) + (utility ? separatorWidth : 0);
    }

    // TasksModel may build its initial manual map while QML is still applying
    // launcher/sort bindings. Restore the supplied order without syncLaunchers(),
    // which would rewrite the original URLs or persist window tasks as pins.
    TaskManager.TasksModel {
        id: tasks
        objectName: "nativeTasksModel"
        launcherList: root.launchers
        sortMode: TaskManager.TasksModel.SortManual
        groupMode: TaskManager.TasksModel.GroupApplications
        groupInline: false
        separateLaunchers: false
        launchInPlace: true
        hideActivatedLaunchers: true
        // Include windows on other desktops so pins never disappear on switching.
        filterByVirtualDesktop: false
        filterByActivity: false
        filterByScreen: false
    }
    // Model signals arrive in bursts (a window title can change many times a second): batch them so the
    // icon list is sorted once per burst instead of once per signal.
    Timer {
        id: refreshTimer
        interval: 30
        onTriggered: root.revision++
    }
    Connections {
        target: tasks
        function onDataChanged() { refreshTimer.restart(); }
        function onRowsInserted() { refreshTimer.restart(); }
        function onRowsRemoved() { refreshTimer.restart(); }
        function onRowsMoved() { refreshTimer.restart(); }
        function onModelReset() { refreshTimer.restart(); }
        function onLayoutChanged() { refreshTimer.restart(); }
        function onCountChanged() { refreshTimer.restart(); }
    }
    HoverHandler { id: hover; acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad }

    // Glass in the macOS style: a soft shadow under the body, a gently lighter top, no hard outline,
    // and one light shine that fades out along the top edge only.
    Rectangle {
        id: glass
        objectName: "dockGlass"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        width: row.width + root.padding * 2 - root.gap
        height: root.idleHeight
        radius: root.radiusPx
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#c83a3a40" }
            GradientStop { position: 1.0; color: "#c41c1c20" }
        }
        border.width: 0
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: "#66000000"
            shadowBlur: 0.7
            shadowVerticalOffset: 3
            shadowHorizontalOffset: 0
            shadowScale: 1.0
        }
        // Top shine: bright at the centre, fading toward both corners; there is no bottom line.
        Rectangle {
            objectName: "dockShine"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: root.radiusPx
            anchors.rightMargin: root.radiusPx
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#00ffffff" }
                GradientStop { position: 0.5; color: "#38ffffff" }
                GradientStop { position: 1.0; color: "#00ffffff" }
            }
        }
    }
    Row {
        id: row
        objectName: "iconRow"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        // As widths grow, neighbours move aside; the bottom baseline never moves.
        Repeater {
            id: appRepeater
            model: root.appRows
            delegate: DockIcon {
                required property int index
                required property int modelData   // TasksModel row
                objectName: "taskIcon-" + index
                iconSource: root.role(modelData, Qt.DecorationRole)
                label: String(root.role(modelData, Qt.DisplayRole) || root.role(modelData, TaskManager.AbstractTasksModel.AppName) || "Application")
                baseIconSize: root.baseIconSize
                gap: root.gap
                canvasHeight: root.canvasHeight
                bottomInset: root.iconBottomInset
                dotInset: root.dotInset
                showDots: root.showRunningDots
                zoomFactor: root.zoomFactor
                pointerX: root.pointerX
                pointerInside: root.pointerInside
                restingCenter: root.centerFor(index, false)
                running: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsWindow) || root.role(modelData, TaskManager.AbstractTasksModel.IsGroupParent))
                active: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsActive))
                grouped: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsGroupParent))
                attention: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsDemandingAttention))
                onActivated: newInstance => root.activateTask(modelData, newInstance)
            }
        }
        Item {
            objectName: "utilitySeparator"
            visible: root.hasUtilities
            width: visible ? root.separatorWidth : 0
            height: root.canvasHeight
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Math.round(root.idleHeight * 0.15)
                width: 1
                height: root.idleHeight * 0.7
                color: "#50ffffff"
                Rectangle { x: 1; width: 1; height: parent.height; color: "#50000000" }
            }
        }
        Repeater {
            model: root.utilityRows
            delegate: DockIcon {
                required property int index
                required property int modelData   // TasksModel row
                objectName: "utilityTaskIcon-" + index
                iconSource: root.role(modelData, Qt.DecorationRole)
                label: String(root.role(modelData, Qt.DisplayRole) || root.role(modelData, TaskManager.AbstractTasksModel.AppName) || "Application")
                baseIconSize: root.baseIconSize
                gap: root.gap
                canvasHeight: root.canvasHeight
                bottomInset: root.iconBottomInset
                dotInset: root.dotInset
                showDots: root.showRunningDots
                zoomFactor: root.zoomFactor
                pointerX: root.pointerX
                pointerInside: root.pointerInside
                restingCenter: root.centerFor(index, true)
                running: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsWindow) || root.role(modelData, TaskManager.AbstractTasksModel.IsGroupParent))
                active: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsActive))
                grouped: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsGroupParent))
                attention: Boolean(root.role(modelData, TaskManager.AbstractTasksModel.IsDemandingAttention))
                onActivated: newInstance => root.activateTask(modelData, newInstance)
            }
        }
        DockIcon {
            objectName: "downloadsIcon"
            visible: root.showDownloads
            iconSource: "folder-downloads"
            label: "Downloads"
            baseIconSize: root.baseIconSize
            gap: root.gap
            canvasHeight: root.canvasHeight
            bottomInset: root.iconBottomInset
            dotInset: root.dotInset
            zoomFactor: root.zoomFactor
            pointerX: root.pointerX
            pointerInside: root.pointerInside
            restingCenter: root.centerFor(root.utilityCount, true)
            onActivated: Qt.openUrlExternally(StandardPaths.writableLocation(StandardPaths.DownloadLocation))
        }
        DockIcon {
            objectName: "trashIcon"
            visible: root.showTrash
            iconSource: "user-trash"
            label: "Trash"
            baseIconSize: root.baseIconSize
            gap: root.gap
            canvasHeight: root.canvasHeight
            bottomInset: root.iconBottomInset
            dotInset: root.dotInset
            zoomFactor: root.zoomFactor
            pointerX: root.pointerX
            pointerInside: root.pointerInside
            restingCenter: root.centerFor(root.utilityCount + (root.showDownloads ? 1 : 0), true)
            onActivated: Qt.openUrlExternally("trash:/")
        }
    }
}
