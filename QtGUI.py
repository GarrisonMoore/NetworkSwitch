import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QGridLayout,
    QDialog, QFormLayout, QCheckBox, QComboBox, QListWidgetItem, QListWidget, QScrollArea
)
from PySide6.QtCore import Qt
from Router import RouterUnit, NetworkBackend, PortJack, NetworkInterface

backend = NetworkBackend()
routers = [RouterUnit(iface, ports_quant=20) for iface in backend.get_all_interfaces()]

# --- UI Color Palette ---
BG_CANVAS = "#808080"  # Medium grey rack background
BG_CHASSIS = "#1e1e1e"  # Dark charcoal router unit housing
BG_PORT_HOUSING = "#2b2f36"  # Gunmetal outer RJ45 cage
BG_PORT_RECESS = "#1f2229"  # Dark recessed inner port face
BG_PORT_CAVITY = "#0d0e11"  # Near-black RJ45 socket interior
BG_LED_HOUSING = "#111317"  # Dark LED bezel

# Metallic Bevel Highlights & Shadows
METAL_LIGHT_TOP = "#c4ccd4"  # Bright brushed-steel top edge
METAL_LIGHT_LEFT = "#aeb6bf"  # Silver-grey left edge
METAL_DARK_BOT = "#141619"  # Deep shadow bottom edge
METAL_DARK_RIGHT = "#181b20"  # Dark iron right edge
METAL_TRIM = "#5a626e"  # Mid-tone steel inner trim
SOCKET_OUTLINE = "#6c7582"  # Light steel socket rim
LED_OUTLINE = "#4a5058"  # Muted steel LED rim

# Port Accents, Pins & Status LEDs
ACCENT_WAN = "#d97706"  # Amber / orange WAN stripe
ACCENT_LAN = "#f3f4f6"  # Crisp off-white LAN stripe
GOLD_PIN = "#d4af37"  # Metallic gold RJ45 contact pins
LED_ACTIVE = "#00ff00"  # Bright green traffic LED
LED_OFF = "#1a241a"  # Unlit dark LED

# Rocker Switch Colors
SWITCH_BEZEL = "#111317"  # Dark plastic outer switch housing
SWITCH_RED_HIGH = "#ef4444"  # Lit / raised crimson half
SWITCH_RED_MID = "#b91c1c"  # Unlit raised red half
SWITCH_RED_SHADOW = "#7f1d1d"  # Pressed-in dark red half
SWITCH_HIGHLIGHT = "#fca5a5"  # Top edge specular highlight
SWITCH_CREASE = "#3b0707"  # Center pivot divider line

def truncate_text(text: str, max_len: int = 15) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "..."

class PortWidget(QFrame):
    def __init__(self, jack: PortJack, accent_color: str = ACCENT_LAN):
        super().__init__()
        self.jack = jack
        self.setFixedSize(25, 25)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"background-color: #0d0e11; border: 2px solid {accent_color}; border-radius: 3px;")

    def mousePressEvent(self, event):

        is_local = "Local" if self.jack.interface.is_local else "Discovered"

        if event.button() == Qt.MouseButton.RightButton:
            dialog = PortConfigWindow(self.jack, parent=self)
            if dialog.exec():
                state = "Enabled" if self.jack.enabled else "Disabled"
                print(
                    f"[Clicked: {self.jack.jack_id}] "
                    f"[State: {state}] "
                    f"[{self.jack.protocol}] "
                    f"[{self.jack.allowed_sources}] "
                    f"[{self.jack.target_port}] "
                    f"[{self.jack.connected_cable}]"
                    f"[{is_local}]")
        super().mousePressEvent(event)

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
        self.port_entry.setText(str(jack.target_port))
        layout.addRow("Listen Port:" if is_local else "Port:", self.port_entry)

        if is_local:
            # Whitelist Entries
            self.whitelist_entry = QLineEdit()
            self.whitelist_entry.setPlaceholderText("IP/CIDR + Enter")
            self.whitelist_entry.returnPressed.connect(self.add_whitelist_entry)
            layout.addRow("Sources:", self.whitelist_entry)

            self.whitelist = QListWidget()
            self.whitelist.addItems(jack.allowed_sources)
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

    def save_config(self, is_local: bool):
        """
        Saves the current configuration to the Jack instance.
        """
        if is_local:
            self.add_whitelist_entry()
            self.jack.enabled = self.enabled_cb.isChecked()
            self.jack.protocol = self.protocol_box.currentText()
            self.jack.target_port = self.port_entry.text().strip()
            self.jack.allow_deny = self.allow_deny_box.currentText()
            self.jack.allowed_sources = [self.whitelist.item(i).text() for i in range(self.whitelist.count())]
        else:
            self.jack.target_port = self.port_entry.text().strip()

        self.accept()


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # main outer layout
        container = QWidget()
        self.main_layout = QHBoxLayout(container)

        # Local NICs
        self.local_rack = QVBoxLayout()
        self.local_rack.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.local_rack_label = QLabel("Local NICs")
        self.local_rack_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        self.local_rack_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.local_rack.addWidget(self.local_rack_label)
        self.main_layout.addLayout(self.local_rack)

        # Discovered LAN Hosts
        self.remote_rack = QVBoxLayout()
        self.remote_rack.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.remote_rack_label = QLabel("Discovered LAN Hosts")
        self.remote_rack_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        self.remote_rack_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.remote_rack.addWidget(self.remote_rack_label)
        self.main_layout.addLayout(self.remote_rack)

        # necessary idk why
        scroll_area = QScrollArea()
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(scroll_area)

    def create_router_chassis(self, router: RouterUnit) -> QFrame:
        """
        Creates the interface on the rack using QFrame
        """
        status = "[UP]" if router.interface.is_up else "[DOWN]"
        iface = router.interface

        # 1. Create the box widget
        chassis_box = QFrame()
        chassis_box.setFixedHeight(100)
        chassis_box.setStyleSheet("""
                    QFrame {
                        background-color: #262a32;
                        border: 2px solid #5a626e;
                        border-radius: 6px;
                    }
                """)

        # 2. Give the box a layout so it holds items inside it
        grid = QGridLayout(chassis_box)
        label = QLabel(f"{iface.name} {status}\n"
                       f"{iface.ip_addr}\n"
                       f"{iface.mac_addr}\n"
                       f"{truncate_text(iface.mac_vendor)}")

        label.setFixedWidth(150)
        grid.addWidget(label, 0, 0, 2, 1)

        for i in range(10):
            grid.addWidget(PortWidget(router.jacks[i], ACCENT_LAN), 0, i + 1)
            grid.addWidget(PortWidget(router.jacks[i + 10], ACCENT_LAN), 1, i + 1)

        grid.setColumnStretch(11, 1)
        return chassis_box

    def populate_local_rack(self, local_routers: list[RouterUnit]):
        for router in local_routers:
            chassis_box = self.create_router_chassis(router)
            self.local_rack.addWidget(chassis_box)

    def create_discovery_rack(self):
        """
        Creates the ISP bay using QFrame
        """

        default_routes = backend.get_default_interface()
        if not default_routes:
            return

        discovered_ifaces = backend.scan_subnet(default_routes[0])
        remote_routers = [RouterUnit(iface, ports_quant=20) for iface in discovered_ifaces]

        for router in remote_routers:
            self.remote_rack.addWidget(self.create_router_chassis(router))


if __name__ == "__main__":
    # You need one (and only one) QApplication instance per application.
    # Pass in sys.argv to allow command line arguments for your app.
    # If you know you won't use command line arguments QApplication([]) works too.
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #f3f4f6;
        }
        QLabel {
            background-color: transparent;
            color: #f3f4f6;
        }
    """)

    # Create a Qt widget, which will be our window.
    window = MainWindow()
    window.populate_local_rack(routers)
    window.create_discovery_rack()

    # windows are hidden by default
    window.show()

    app.exec()
