"""Build tiny authored PCAPs; no network capture or transmission occurs."""

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "tracks/cyber-tracks/materials"


def checksum(data):
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack("!" + "H" * (len(data) // 2), data))
    while total >> 16:
        total = (total & 65535) + (total >> 16)
    return (~total) & 65535


def tcp(src, dst, sport, dport, seq, ack, flags, payload=b""):
    header = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 80, flags, 8192, 0, 0)
    pseudo = src + dst + struct.pack("!BBH", 0, 6, len(header) + len(payload))
    header = (
        header[:16]
        + struct.pack("!H", checksum(pseudo + header + payload))
        + header[18:]
    )
    ip = struct.pack("!BBHHHBBH", 69, 0, 40 + len(payload), 1, 0, 64, 6, 0) + src + dst
    ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
    return bytes.fromhex("0200000000200200000000100800") + ip + header + payload


def pcap(packets, linktype):
    output = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, linktype)
    for index, packet in enumerate(packets):
        output += (
            struct.pack("<IIII", 1790845200 + index, 0, len(packet), len(packet))
            + packet
        )
    return output


def fixtures():
    client, server = bytes([192, 0, 2, 10]), bytes([192, 0, 2, 20])
    packets = []
    for port, path, status, body in [
        (40001, "/", "200 OK", "Training page\n"),
        (40002, "/missing", "404 Not Found", "Not found\n"),
    ]:
        request = f"GET {path} HTTP/1.1\r\nHost: training.invalid\r\nConnection: close\r\n\r\n".encode()
        response = f"HTTP/1.1 {status}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}".encode()
        packets.extend(
            [
                tcp(client, server, port, 80, 100, 0, 2),
                tcp(server, client, 80, port, 200, 101, 18),
                tcp(client, server, port, 80, 101, 201, 16),
                tcp(client, server, port, 80, 101, 201, 24, request),
                tcp(server, client, 80, port, 201, 101 + len(request), 24, response),
                tcp(
                    server,
                    client,
                    80,
                    port,
                    201 + len(response),
                    101 + len(request),
                    17,
                ),
                tcp(
                    client,
                    server,
                    port,
                    80,
                    101 + len(request),
                    202 + len(response),
                    17,
                ),
                tcp(
                    server,
                    client,
                    80,
                    port,
                    202 + len(response),
                    102 + len(request),
                    16,
                ),
            ]
        )
    # Beacon: SSID, supported rate, channel, WPA2/CCMP RSN parameters. No radio data.
    mac = bytes.fromhex("020000000001")
    header = b"\x80\x00\x00\x00" + b"\xff" * 6 + mac + mac + b"\x00\x00"
    fixed = struct.pack("<QHH", 0, 100, 0x11)
    ssid = b"Ascend-Training"
    tags = (
        b"\x00"
        + bytes([len(ssid)])
        + ssid
        + bytes.fromhex("01018203010630140100000fac040100000fac040100000fac020000")
    )
    return {
        "http-training.pcap": pcap(packets, 1),
        "wifi-beacon.pcap": pcap([header + fixed + tags], 105),
    }


if __name__ == "__main__":
    for name, content in fixtures().items():
        tracks = (
            [
                "networking-for-security",
                "defensive-security-and-detection",
                "wireless-iot-security",
            ]
            if name.startswith("http")
            else ["networking-for-security", "wireless-iot-security"]
        )
        for track in tracks:
            folder = ROOT / track
            folder.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(content)
    print("Synthetic packet fixtures generated without network traffic.")
