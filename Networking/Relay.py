import asyncio
import ipaddress

from Networking.Objects import PortJack


class PatchCable:
    """
    Represents a physical connection between two PortJacks.

    Will use a layer 4 TCP reverse proxy to route traffic between the two PortJacks.
    """

    def __init__(self, source_jack: PortJack, dest_jack: PortJack):
        if not source_jack.interface.is_local or dest_jack.interface.is_local:
            raise ValueError("PatchCable must connect a local PortJack to a remote PortJack.")

        self.source_jack = source_jack
        self.dest_jack = dest_jack
        self.active = False
        self._server = None

        self.source_jack.connected_cable = self
        self.dest_jack.connected_cable = self

    def is_client_allowed(self, client_ip: str) -> bool:
        client = ipaddress.ip_address(client_ip)
        matched = any(
            client in ipaddress.ip_network(entry, strict=False)
            for entry in self.source_jack.target_ips
        )

        if self.source_jack.allow_deny == "Allow":
            return matched
        else:
            return not matched

    async def pipe(self, reader, writer):
        try:
            while data := await reader.read(4096):
                writer.write(data)
                await writer.drain()
        finally:
            writer.close()


    async def handle_client(self, local_reader, local_writer):
        client_ip = local_writer.get_extra_info("peername")[0]

        if not self.source_jack.enabled or not self.is_client_allowed(client_ip):
            local_writer.close()
            return

        remote_reader, remote_writer = await(
            asyncio.open_connection(self.dest_jack.interface.ip_addr,
                                    int(self.dest_jack.port))
        )
        await(asyncio.gather(self.pipe(local_reader, remote_writer),
                             self.pipe(remote_reader, local_writer)))


    async def start_relay(self):
        self._server = await(asyncio.start_server(
            self.handle_client,
            self.source_jack.interface.ip_addr,
            int(self.source_jack.port))
        )
        self.active = True

        async with self._server:
            await self._server.serve_forever()

    async def stop_relay(self):
        self.active = False
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self.source_jack.connected_cable = None
        self.dest_jack.connected_cable = None