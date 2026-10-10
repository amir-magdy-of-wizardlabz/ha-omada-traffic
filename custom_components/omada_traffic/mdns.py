"""Ask devices on the LAN for their own name (reverse mDNS lookup).

Apple devices that use a private, rotating Wi-Fi address still answer with a
stable name such as "Sams-iPhone.local". This only sends standard mDNS
questions and listens for the replies; it changes nothing on any device.
"""
from __future__ import annotations

import asyncio
import logging
import socket
import struct

_LOGGER = logging.getLogger(__name__)

MDNS_ADDR = ("224.0.0.251", 5353)
TYPE_PTR = 12
CLASS_IN_UNICAST = 0x8001  # IN, with the "reply directly to me" bit


def _question(txid: int, ip: str) -> bytes:
    name = ".".join(reversed(ip.split("."))) + ".in-addr.arpa"
    qname = b"".join(bytes([len(p)]) + p.encode("ascii") for p in name.split(".")) + b"\x00"
    return struct.pack("!HHHHHH", txid, 0, 1, 0, 0, 0) + qname + struct.pack("!HH", TYPE_PTR, CLASS_IN_UNICAST)


def _read_name(data: bytes, pos: int) -> tuple[str, int]:
    """Decode a possibly compressed DNS name; returns (name, position after it)."""
    labels: list[str] = []
    end = None
    for _ in range(64):  # bound pointer chains
        length = data[pos]
        if length == 0:
            pos += 1
            break
        if length & 0xC0 == 0xC0:
            if end is None:
                end = pos + 2
            pos = ((length & 0x3F) << 8) | data[pos + 1]
            continue
        labels.append(data[pos + 1:pos + 1 + length].decode("utf-8", "replace"))
        pos += 1 + length
    return ".".join(labels), (end if end is not None else pos)


def _parse(data: bytes) -> list[tuple[str, str]]:
    """Return (owner name, target) for every PTR record in the answer section."""
    _, flags, qd, an, _, _ = struct.unpack("!HHHHHH", data[:12])
    if not flags & 0x8000:
        return []
    pos = 12
    for _ in range(qd):
        _, pos = _read_name(data, pos)
        pos += 4
    out = []
    for _ in range(an):
        owner, pos = _read_name(data, pos)
        rtype, _, _, rdlen = struct.unpack("!HHIH", data[pos:pos + 10])
        pos += 10
        if rtype == TYPE_PTR:
            target, _ = _read_name(data, pos)
            out.append((owner.lower(), target))
        pos += rdlen
    return out


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, wanted: dict[str, str]) -> None:
        self.wanted = wanted  # reverse name -> ip
        self.found: dict[str, str] = {}

    def datagram_received(self, data: bytes, addr) -> None:
        try:
            records = _parse(data)
        except (IndexError, struct.error):
            return
        for owner, target in records:
            ip = self.wanted.get(owner)
            # Only believe a device speaking for itself, not a proxy or a stale cache.
            if ip and addr[0] == ip and target.lower().endswith(".local"):
                self.found[ip] = target[: -len(".local")]


async def reverse_lookup(ips: list[str], timeout: float = 1.5) -> dict[str, str]:
    """Return {ip: name} for the devices that answered within the timeout."""
    ips = [ip for ip in ips if ip and ip.count(".") == 3]
    if not ips:
        return {}
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Send on the interface that faces these devices, not a Docker bridge.
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect((ips[0], 9))
            local_ip = probe.getsockname()[0]
        finally:
            probe.close()
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ip))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        sock.bind((local_ip, 0))
        sock.setblocking(False)
    except OSError as err:
        sock.close()
        _LOGGER.debug("mDNS socket setup failed: %s", err)
        return {}
    wanted = {".".join(reversed(ip.split("."))) + ".in-addr.arpa": ip for ip in ips}
    transport, protocol = await loop.create_datagram_endpoint(lambda: _Protocol(wanted), sock=sock)
    try:
        for i, ip in enumerate(ips):
            transport.sendto(_question(i + 1, ip), MDNS_ADDR)
        await asyncio.sleep(timeout)
    finally:
        transport.close()
    return protocol.found
