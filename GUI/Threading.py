import asyncio
from PySide6.QtCore import QThread, Signal
from Networking.Backend import NetworkBackend
from Networking.Objects import NetworkInterface
from Networking.Relay import PatchCable


class ScanWorker(QThread):
    finished = Signal(list)

    def __init__(self, backend: NetworkBackend, default_route: NetworkInterface):
        super().__init__()
        self.backend = backend
        self.default_route = default_route

    def run(self):
        discovered_ifaces = self.backend.scan_subnet(self.default_route)
        self.finished.emit(discovered_ifaces)

class AsyncRelayThread(QThread):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_cable(self, cable: PatchCable):
        asyncio.run_coroutine_threadsafe(cable.start_relay(), self.loop)

    def stop_cable(self, cable: PatchCable):
        asyncio.run_coroutine_threadsafe(cable.stop_relay(), self.loop)
