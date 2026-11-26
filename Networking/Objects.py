class NetworkInterface:
    """
    Represents a network interface with attributes such as name, MAC address, IP address, MAC vendor, and status.
    """

    def __init__(self, name: str, mac_addr: str = "00:00:00:00:00:00", mac_vendor: str = "Unknown Vendor",
                 ip_addr: str = None, is_up: bool = False, is_local: bool = True):
        self.name = name
        self.mac_addr = mac_addr
        self.ip_addr = ip_addr
        self.mac_vendor = mac_vendor
        self.is_up = is_up
        self.is_local = is_local
        self.connected_port = None

    def __str__(self) -> str:
        status = "UP" if self.is_up == True else "DOWN"
        ip = self.ip_addr if self.ip_addr else "NO IP"
        return f"{self.name} [{status}] - {ip} ({self.mac_addr}) [{self.mac_vendor}]"


class PortJack:
    """
    Replicates an RJ45 port on my virtual interface
    """

    def __init__(self, jack_id: str, interface: NetworkInterface):
        self.jack_id = jack_id
        self.interface = interface

        # port forwarding
        self.enabled = False
        self.port: str = ""
        self.allow_deny: str = "Allow"
        self.target_ips = []
        self.protocol = None  # UDP or TCP
        # connection state
        self.connected_cable = None

    def __repr__(self):
        return f"<PortJack {self.jack_id}>"


class RouterUnit:
    """
    Defines a single 'router' which is assigned to a single network interface.
    """

    def __init__(self, interface: NetworkInterface, ports_quant=3):
        self.interface = interface
        self.jacks = [
            PortJack(f"{interface.name}_LAN{i + 1}", interface)
            for i in range(ports_quant)
        ]

    def all_jacks(self) -> list[PortJack]:
        """
        Returns a list of all PortJacks
        """
        return self.jacks

