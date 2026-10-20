#!/usr/bin/env python3
"""Connect to a QEMU socket netdev and inject raw Ethernet frames.

QEMU must be listening on 127.0.0.1:PORT, which the justfile recipe
'just qemu' sets up with:

    -netdev socket,id=n1,listen=127.0.0.1:PORT
    -device virtio-net-device,netdev=n1,bus=virtio-mmio-bus.0

Manual workflow (two terminals):

    just qemu          # terminal 1: boot the guest, keep it running
    just inject        # terminal 2: one plain 1514-byte frame
    just inject-vlan   # terminal 2: one VLAN-tagged 1518-byte frame
"""
import argparse
import socket
import struct
import sys
import time


def build_frame(tagged):
    dst = b"\xff" * 6
    src = b"\x02\x00\x00\x00\x00\x01"
    if tagged:
        hdr = dst + src + b"\x81\x00" + struct.pack(">H", 100) + b"\x08\x00"
        total = 1518
    else:
        hdr = dst + src + b"\x08\x00"
        total = 1514
    payload = bytes(i & 0xFF for i in range(total - len(hdr)))
    frame = hdr + payload
    assert len(frame) == total, len(frame)
    return frame


def main():
    parser = argparse.ArgumentParser(description="inject raw frames into a QEMU socket netdev")
    parser.add_argument("--port", type=int, default=45987)
    parser.add_argument("--vlan", action="store_true", help="send a VLAN-tagged 1518-byte frame")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    frame = build_frame(args.vlan)
    label = "VLAN tagged 1518B" if args.vlan else "plain 1514B"

    deadline = time.time() + args.timeout
    sock = None
    while time.time() < deadline:
        try:
            sock = socket.create_connection(("127.0.0.1", args.port), timeout=1)
            break
        except OSError:
            time.sleep(0.1)

    if sock is None:
        print("ERROR: cannot connect to 127.0.0.1:%d" % args.port, file=sys.stderr)
        print("       is 'just qemu' running in another terminal?", file=sys.stderr)
        return 2

    for _ in range(args.count):
        sock.sendall(struct.pack(">I", len(frame)) + frame)
        print("sent %s frame, %d bytes" % (label, len(frame)))

    sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
