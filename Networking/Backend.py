import asyncio
import ipaddress
import json
import os
import platform
import socket
import subprocess
import time
from concurrent.futures.thread import ThreadPoolExecutor
import psutil
import requests
from Networking.Objects import NetworkInterface, PortJack, RouterUnit
from Networking.Relay import PatchCable

from Utils import Decorators

timer = Decorators.timer
verbose = Decorators.verbose_mode

os_name = platform.system()

class NetworkBackend:
    """
    Represents a network backend with attributes such as dry_run and methods to get network interfaces, resolve MAC vendor,
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def get_all_interfaces(self) -> list[NetworkInterface]:
        """
        Returns a list of NetworkInterface Objects
        """
        interfaces = []
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
                name=name,
                mac_addr=mac_addr,
                mac_vendor=mac_vendor,
                ip_addr=ip_addr,
                is_up=isup
            )
            interfaces.append(iface)

        return interfaces

    def get_default_interface(self) -> list[NetworkInterface]:
        """
        Gets the returns a list of the defualt routes as NetworkInterface objects
        """
        default_ifaces = []

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                outbound_ip = s.getsockname()[0]

            for iface in self.get_all_interfaces():
                if iface.ip_addr == outbound_ip and iface not in default_ifaces:
                    default_ifaces.append(iface)

        except OSError:
            pass

        return default_ifaces

    @timer
    def resolve_mac_vendor(self, mac_addr: str) -> str:
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

    def save_oui_cache(self, oui_cache: dict[str, str]):
        """
        Saves the OUI cache to the file
        """
        with open("oui_cache.json", "w") as f:
            json.dump(oui_cache, f, indent=2)

    def load_oui_cache(self) -> dict[str, str]:
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

    @staticmethod
    def ping(ip: str):
        """
        Helper method to ping a host on a network
        """
        flag_count = "-n" if os_name == "Windows" else "-c"
        flag_wait = "-w" if os_name == "Windows" else "-W"
        timeout = "300" if os_name == "Windows" else "1"

        subprocess.run(
            ["ping", flag_count, "1", flag_wait, timeout, ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    @timer
    def scan_subnet(self, default_route: NetworkInterface) -> list[NetworkInterface]:
        """
        Scans the default routes network for devices and turns them into network interface objects

        Executes a ping sweep of the subnet and then reads the arp cache to get each hosts metadata
        """
        if not default_route or not default_route.ip_addr:
            return []

        # get the subnet of the default routes IP
        subnet = ipaddress.IPv4Network(f"{default_route.ip_addr}/24", strict=False)

        # loop through the subnet and put each host in a list
        target_ips = [str(ip) for ip in subnet.hosts() if str(ip) != default_route.ip_addr]

        # start a ping sweep of the subnet on a thread pool
        with ThreadPoolExecutor(max_workers=64) as pool:
            pool.map(NetworkBackend.ping, target_ips)

        # read the arp cache to get each hosts metadata
        arp_output = subprocess.check_output(["arp", "-a"], text=True, stderr=subprocess.DEVNULL)
        local_ips = {iface.ip_addr for iface in self.get_all_interfaces() if iface.ip_addr}
        hosts = []

        # parse the arp cache output
        for line in arp_output.splitlines():
            parts = line.replace("(", "").replace(")", "").split()
            ip = next((p for p in parts if p.count(".") == 3), None)
            mac = next((p.replace("-", ":").lower() for p in parts if p.count(":") == 5 or p.count("-") == 5), None)

            if ip and mac and mac != "ff:ff:ff:ff:ff:ff" and ip not in local_ips:
                try:
                    name = socket.gethostbyaddr(ip)[0]
                except OSError:
                    name = ip

                # turn the resolved host into a NetworkInterface object
                hosts.append(
                    NetworkInterface(
                        name=name,
                        mac_addr=mac,
                        mac_vendor=self.resolve_mac_vendor(mac),
                        ip_addr=ip,
                        is_up=True,
                        is_local=False
                    )
                )
        print(hosts)
        return hosts



async def test_relay():
    local_nic = NetworkInterface("test_local", ip_addr="127.0.0.1", is_up=True, is_local=True)
    remote_host = NetworkInterface("printer", ip_addr="10.0.0.109", is_up=True, is_local=False)

    src_jack = PortJack("local_1", local_nic)
    src_jack.enabled = True
    src_jack.port = "8147"
    src_jack.allow_deny = "Allow"
    src_jack.target_ips = ["127.0.0.1"]

    dst_jack = PortJack("remote_1", remote_host)
    dst_jack.port = "80"

    cable = PatchCable(src_jack, dst_jack)
    print("Relaying 127.0.0.1:8080 -> 10.0.0.109:80 ... Press Ctrl+C to stop.")
    await cable.start_relay()


if __name__ == "__main__":
    backend = NetworkBackend()
    interfaces = backend.get_all_interfaces()

    # show interfaces
    print("\nInterfaces:")
    for iface in interfaces:
        print(iface)

    # get default route
    default_route = backend.get_default_interface()
    print(f"\nDefault routes:\n{default_route}\n")

    # testing portjacks
    routers = []
    for iface in interfaces:
        router = RouterUnit(iface)
        routers.append(router)

        print(f"{router.all_jacks()}")

    print("")

    # testing subnet scanning
    for iface in default_route:
        if iface.is_up and iface.ip_addr:
            print(f"Scanning subnet for {iface.name} ({iface.ip_addr})...")
            alive = backend.scan_subnet(iface)
            for host in alive:
                print(f"Found host: {host}")

    asyncio.run(test_relay())
