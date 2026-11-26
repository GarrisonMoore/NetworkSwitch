from PySide6.QtWidgets import QFrame, QDialog, QLineEdit, QLabel, QCheckBox, QComboBox, QFormLayout, QListWidget, QPushButton
from PySide6.QtCore import Qt, Signal

from Networking.Objects import PortJack

ACCENT_WAN = "#d97706"  # Amber / orange WAN stripe
ACCENT_LAN = "#f3f4f6"  # Crisp off-white LAN stripe
LED_ACTIVE = "#00ff00"  # Bright green traffic LED
CABLE_STANDBY = "#38bdf8"  # Cyan connected-but-disabled wire

class PortWidget(QFrame):
    drag_started = Signal(object)
    drag_moved = Signal(object)  # QPoint in global screen coords
    drag_released = Signal(object, object)  # (start_port_widget, global_pos)

    def __init__(self, jack: PortJack, accent_color: str = ACCENT_LAN):
        super().__init__()
        self.jack = jack
        self.default_accent = accent_color
        self.is_selected = False
        self.dragging = False
        self.setFixedSize(25, 25)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"background-color: #0d0e11; border: 2px solid {accent_color}; border-radius: 3px;")
        self.refresh_style()

    def refresh_style(self):
        if self.is_selected:
            border = ACCENT_WAN  # Amber: actively dragging
        elif self.jack.connected_cable is not None:
            border = LED_ACTIVE if self.jack.enabled else CABLE_STANDBY  # Green/Cyan: wired
        elif self.jack.interface.is_local and self.jack.enabled:
            border = LED_ACTIVE  # Green: local rule enabled
        elif not self.jack.interface.is_local and self.jack.port:
            border = "#a855f7"  # Purple: remote port configured & ready
        else:
            border = self.default_accent  # White: unconfigured
        self.setStyleSheet(f"background-color: #0d0e11; border: 2px solid {border}; border-radius: 3px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if (
                self.jack.interface.is_local
                and self.jack.port
                and self.jack.connected_cable is None
            ):
                self.dragging = True
                self.is_selected = True
                self.refresh_style()
                self.drag_started.emit(self)

        elif event.button() == Qt.MouseButton.RightButton:
            dialog = PortConfigWindow(self.jack, parent=self)
            if dialog.exec():
                self.refresh_style()
                if self.jack.connected_cable is not None:
                    self.window().cable_overlay.update()

        elif event.button() == Qt.MouseButton.MiddleButton and self.jack.connected_cable is not None:
            self.window().disconnect_cable(self.jack.connected_cable)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.drag_moved.emit(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.is_selected = False
            self.refresh_style()
            self.drag_released.emit(self, event.globalPosition().toPoint())
        super().mouseReleaseEvent(event)

class PortConfigWindow(QDialog):
    def __init__(self, jack: PortJack, parent=None):
        super().__init__()

        self.jack = jack
        is_local = self.jack.interface.is_local

        self.setWindowTitle("Port Configuration")
        layout = QFormLayout(self)

        if is_local:
            # Enable / Disable Checkbox
            self.enabled_cb = QCheckBox("Enable / Disable Rule")
            self.enabled_cb.setChecked(self.jack.enabled)
            layout.addRow(self.enabled_cb)

            # Allow / Deny Selection
            self.allow_deny_box = QComboBox()
            self.allow_deny_box.addItems(["Allow", "Deny"])
            layout.addRow(self.allow_deny_box)

            # Protocol Selection
            self.protocol_box = QComboBox()
            self.protocol_box.addItems(["TCP", "UDP", "ANY"])
            if jack.protocol in ["TCP", "UDP", "ANY"]:
                self.protocol_box.setCurrentText(jack.protocol)
            layout.addRow(self.protocol_box)

        # Port Selection
        self.port_entry = QLineEdit()
        self.port_entry.setText(str(jack.port))
        layout.addRow("Listen Port:" if is_local else "Port:", self.port_entry)

        if is_local:
            # Whitelist Entries
            self.whitelist_entry = QLineEdit()
            self.whitelist_entry.setPlaceholderText("IP/CIDR + Enter")
            self.whitelist_entry.returnPressed.connect(self.add_whitelist_entry)
            layout.addRow("Sources:", self.whitelist_entry)

            self.whitelist = QListWidget()
            self.whitelist.addItems(jack.target_ips)
            self.whitelist.itemDoubleClicked.connect(self.remove_whitelist_entry)
            layout.addRow(self.whitelist)

        else:
            # if portjack is on a remote interface only allow configuring port, default target ip to the interface IP
            self.target_ip = QLabel(f"{jack.interface.ip_addr}")
            layout.addRow("Target: ", self.target_ip)

        save_btn = QPushButton("Save")
        save_btn.setAutoDefault(False)
        save_btn.setDefault(False)
        save_btn.clicked.connect(self.save_config)
        layout.addRow(save_btn)

    def add_whitelist_entry(self):
        """
        Adds a whitelist entry to the list widget.

        TODO: Implement validation and error handling. Should check the entered format and ensure it's a valid IP/CIDR.
        """
        entry = self.whitelist_entry.text()
        if entry:
            existing = [self.whitelist.item(i).text() for i in range(self.whitelist.count())]
            if entry not in existing:
                self.whitelist.addItem(entry)
            self.whitelist_entry.clear()

    def remove_whitelist_entry(self, item):
        """
        Removes a whitelist entry from the list widget.
        """
        self.whitelist.takeItem(self.whitelist.row(item))

    def save_config(self):
        """
        Saves the current configuration to the Jack instance.
        """
        if self.jack.interface.is_local:
            self.add_whitelist_entry()
            self.jack.enabled = self.enabled_cb.isChecked()
            self.jack.protocol = self.protocol_box.currentText()
            self.jack.port = self.port_entry.text().strip()
            self.jack.allow_deny = self.allow_deny_box.currentText()
            self.jack.target_ips = [self.whitelist.item(i).text() for i in range(self.whitelist.count())]
        else:
            self.jack.port = self.port_entry.text().strip()

        self.accept()