import os
import platform
import socket
import json
import time
import requests
import psutil
from Utils import Decorators

timer = Decorators.timer
verbose = Decorators.verbose_mode

os_name = platform.system()

class NetworkInterface:
    """
    Represents a network interface with attributes such as name, MAC address, IP address, MAC vendor, and status.
    """
    def __init__(self, name: str, mac_addr: str = "00:00:00:00:00:00", mac_vendor: str = "Unknown Vendor",ip_addr: str = None, is_up: bool = False):
        self.name = name
        self.mac_addr = mac_addr
        self.ip_addr = ip_addr
        self.mac_vendor = mac_vendor
        self.is_up = is_up
        self.connected_port = None

    def __str__(self) -> str:
        status = "UP" if self.is_up == True else "DOWN"
        ip = self.ip_addr if self.ip_addr else "NO IP"
        return f"{self.name} [{status}] - {ip} ({self.mac_addr}) [{self.mac_vendor}]"

class PortJack:
    """
    Replicates an RJ45 port on my virtual interface
    """
    def __init__(self, jack_id: str, jack_type: str, interface: NetworkInterface):
        self.jack_id = jack_id
        self.jack_type = jack_type
        self.interface = interface

        self.target_port: str = ""
        self.protocol = None # UDP or TCP

        # connection state
        self.connected_cable = None

    def __repr__(self):
        return f"<PortJack {self.jack_id}>"

class RouterUnit:
    """
    Defines a single 'router' which is assigned to a single network interface.
    """
    def __init__(self, interface: NetworkInterface, lan_ports_quant = 3):
        self.interface = interface
        self.WAN_jack = PortJack(f"{interface.name}_WAN", "WAN", interface)
        self.LAN_jacks = [
            PortJack(f"{interface.name}_LAN{i + 1}", "LAN", interface)
            for i in range(lan_ports_quant)
        ]

    def all_jacks(self) -> list[PortJack]:
        """
        Returns a list of all PortJacks
        """
        return [self.WAN_jack] + self.LAN_jacks

class NetworkBackend:
    """
    Represents a network backend with attributes such as dry_run and methods to get network interfaces, resolve MAC vendor,
    """
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def get_interfaces(self) -> list[NetworkInterface]:
        """
        Returns a list of NetworkInterface Objects
        """
        interfaces=[]
        stats = psutil.net_if_stats()

        for name, addr_list in psutil.net_if_addrs().items():
            if name == "lo" or "loopback" in name.lower():
                continue

            mac_addr = None
            ip_addr = None

            for addr in addr_list:
                if addr.family == psutil.AF_LINK:
                    mac_addr = addr.address.replace("-", ":").lower()
                elif addr.family == socket.AF_INET:
                    ip_addr = addr.address

            isup = stats[name].isup if name in stats else False

            mac_vendor = self.resolve_mac_vendor(mac_addr)

            iface = NetworkInterface(
                name = name,
                mac_addr = mac_addr,
                mac_vendor= mac_vendor,
                ip_addr = ip_addr,
                is_up = isup
            )
            interfaces.append(iface)

        return interfaces

    def get_default_interface(self) -> list[str]:
        """
        Gets the systems default routes
        """
        raw_routes = ""
        default_ifaces = []

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                outbound_ip = s.getsockname()[0]

            for name, addr_list in psutil.net_if_addrs().items():
                for addr in addr_list:
                    if addr.family == socket.AF_INET and addr.address == outbound_ip:
                        if name not in default_ifaces:
                            default_ifaces.append(name)

        except OSError:
            pass

        return default_ifaces

    def save_oui_cache(self, oui_cache: dict[str,str]):
        """
        Saves the OUI cache to the file
        """
        with open("oui_cache.json", "w") as f:
            json.dump(oui_cache, f, indent=2)

    def load_oui_cache(self) -> dict[str,str]:
        """
        Loads the OUI cache from the file
        """
        if os.path.exists("oui_cache.json"):
            try:
                with open("oui_cache.json", "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    @timer
    def resolve_mac_vendor(self,mac_addr: str) -> str:
        """
        Resolves the MAC vendor from the given MAC address
        """
        if not mac_addr or mac_addr == "00:00:00:00:00:00":
            return "Unknown Vendor"

        oui_cache = self.load_oui_cache()

        # check if the mac addr/vendor is already cached
        if mac_addr in oui_cache:
            return oui_cache[mac_addr]

        try:
            url = f"https://api.macvendors.com/{mac_addr}"
            response = requests.get(url)
            # delay to prevent rate limiting on API calls
            time.sleep(1.1)

            if response.status_code == 200:
                # save the returned vendor to the cache
                oui_cache[mac_addr] = response.text.strip()
                self.save_oui_cache(oui_cache)
                return response.text.strip()

            elif response.status_code == 404:
                # save the unknown vendor to the cache
                oui_cache[mac_addr] = "Unknown Vendor"
                self.save_oui_cache(oui_cache)
                return "Unknown Vendor"

            else:
                return "Error resolving vendor"

        except requests.RequestException:
            return "Lookup failed"

if __name__ == "__main__":
    backend = NetworkBackend()
    interfaces = backend.get_interfaces()

    print("\nInterfaces:")
    for iface in interfaces:
        print(iface)

    print(f"\nDefault routes:\n{backend.get_default_interface()}\n")

    routers = []
    for iface in interfaces:
        router = RouterUnit(iface)
        routers.append(router)

        print(f"{router.all_jacks()}")