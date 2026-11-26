import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, QPoint, QEvent
from GUI.Cable import CableOverlay
from GUI.Port import PortWidget
from GUI.Threading import AsyncRelayThread, ScanWorker
from Networking.Backend import RouterUnit, NetworkBackend, PortJack, NetworkInterface, PatchCable



# Port Accents, Pins & Status LEDs
ACCENT_WAN = "#d97706"  # Amber / orange WAN stripe
ACCENT_LAN = "#f3f4f6"  # Crisp off-white LAN stripe
GOLD_PIN = "#d4af37"  # Metallic gold RJ45 contact pins
LED_ACTIVE = "#00ff00"  # Bright green traffic LED
LED_OFF = "#1a241a"  # Unlit dark LED

CABLE_STANDBY = "#38bdf8"  # Cyan connected-but-disabled wire

def truncate_text(text: str, max_len: int = 15) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "..."

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.backend = NetworkBackend()
        self.routers = [RouterUnit(iface, ports_quant=20) for iface in self.backend.get_all_interfaces()]

        self.setWindowTitle("NetworkSwitch")

        self.cables: list[tuple[PortWidget, PortWidget, PatchCable]] = []

        self.relay_thread = AsyncRelayThread()
        self.relay_thread.start()

        # main outer layout
        self.container = QWidget()
        self.main_layout = QHBoxLayout(self.container)

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
        scroll_area.setWidget(self.container)
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(scroll_area)

        # Transparent overlay sits across the entire scrollable rack container
        self.cable_overlay = CableOverlay(self.container, self.cables)
        self.container.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.container and event.type() == QEvent.Type.Resize:
            self.cable_overlay.setGeometry(self.container.rect())
            self.cable_overlay.raise_()
        return super().eventFilter(watched, event)

    def on_drag_started(self, src_widget: PortWidget):
        self.cable_overlay.setGeometry(self.container.rect())
        self.cable_overlay.drag_start_widget = src_widget
        self.cable_overlay.raise_()

    def on_drag_moved(self, global_pos: QPoint):
        self.cable_overlay.drag_cursor_pos = global_pos
        self.cable_overlay.update()

    def on_drag_released(self, src_widget: PortWidget, global_pos: QPoint):
        self.cable_overlay.drag_start_widget = None
        self.cable_overlay.drag_cursor_pos = None

        target = QApplication.widgetAt(global_pos)
        print(f"[Drag Released] Over widget: {target}")

        if (
            isinstance(target, PortWidget)
            and not target.jack.interface.is_local
            and target.jack.port
            and target.jack.connected_cable is None
        ):
            cable = PatchCable(src_widget.jack, target.jack)
            self.cables.append((src_widget, target, cable))
            self.relay_thread.start_cable(cable)

            src_widget.refresh_style()
            target.refresh_style()
            print(
                f"[Wired] {src_widget.jack.interface.ip_addr}:{src_widget.jack.port} "
                f"-> {target.jack.interface.ip_addr}:{target.jack.port}"
            )

        self.cable_overlay.update()

    def disconnect_cable(self, cable: PatchCable):
        self.relay_thread.stop_cable(cable)

        # Find the matching (src_widget, dst_widget, cable) tuple, remove it, and refresh both ports
        for entry in list(self.cables):
            src_widget, dst_widget, c = entry
            if c is cable:
                self.cables.remove(entry)
                cable.source_jack.connected_cable = None
                cable.dest_jack.connected_cable = None
                src_widget.refresh_style()
                dst_widget.refresh_style()
                break

        self.cable_overlay.update()
        print(f"[Unplugged] {cable.source_jack.jack_id} <-> {cable.dest_jack.jack_id}")

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
        label = QLabel(
                f"{status}"
                f"{iface.name}\n"
                f"{iface.ip_addr}\n"
                f"{iface.mac_addr}\n"
                f"{truncate_text(iface.mac_vendor)}"
                )

        label.setFixedWidth(150)
        grid.addWidget(label, 0, 0, 2, 1)

        for i in range(10):
            for row, idx in ((0, i), (1, i + 10)):
                port_w = PortWidget(router.jacks[idx], ACCENT_LAN)
                port_w.drag_started.connect(self.on_drag_started)
                port_w.drag_moved.connect(self.on_drag_moved)
                port_w.drag_released.connect(self.on_drag_released)
                grid.addWidget(port_w, row, i + 1)

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
        default_routes = self.backend.get_default_interface()
        if not default_routes:
            return

        self.remote_rack_label.setText("Discovered LAN Hosts (Scanning...)")
        self.scan_worker = ScanWorker(self.backend, default_routes[0])
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()

    def on_scan_finished(self, discovered_ifaces: list[NetworkInterface]):
        self.remote_rack_label.setText(f"Discovered LAN Hosts ({len(discovered_ifaces)})")
        remote_routers = [RouterUnit(iface, ports_quant=20) for iface in discovered_ifaces]
        for router in remote_routers:
            self.remote_rack.addWidget(self.create_router_chassis(router))
        self.cable_overlay.raise_()


def main():
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
    window.populate_local_rack(window.routers)
    window.create_discovery_rack()

    # windows are hidden by default
    window.show()

    app.exec()
    window.relay_thread.loop.call_soon_threadsafe(window.relay_thread.loop.stop)
    window.relay_thread.wait()
