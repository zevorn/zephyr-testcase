#!/usr/bin/env python3
"""Inject one untagged 1514-byte and one VLAN-tagged 1518-byte frame into a
Zephyr guest running on qemu_riscv64 with virtio-net over MMIO, over QEMU's
socket netdev (raw Ethernet frames, 4-byte big-endian length prefix).

Usage: host.py <zephyr.elf> [label]
"""
import os
import select
import signal
import socket
import struct
import subprocess
import sys
import time

QEMU = os.environ.get("QEMU", "/opt/homebrew/bin/qemu-system-riscv64")
CPU = os.environ.get(
    "QEMU_CPU",
    "rv64i,i=on,m=on,a=on,f=on,d=on,c=on,zicsr=on,zifencei=on,zicntr=on,zkr=on,pmp=on,u=on",
)
PORT = int(os.environ.get("VNET_PORT", "45987"))
TIMEOUT = float(os.environ.get("VNET_TIMEOUT", "30"))


def build_frame(vlan):
    dst = b"\xff" * 6
    src = b"\x02\x00\x00\x00\x00\x01"
    if vlan:
        hdr = dst + src + b"\x81\x00" + struct.pack(">H", 100) + b"\x08\x00"
        payload_len = 1518 - len(hdr)
    else:
        hdr = dst + src + b"\x08\x00"
        payload_len = 1514 - len(hdr)
    payload = bytes((i & 0xFF) for i in range(payload_len))
    frame = hdr + payload
    assert len(frame) == (1518 if vlan else 1514), len(frame)
    return frame


def main():
    elf = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(os.path.dirname(elf))
    cmd = [
        QEMU, "-machine", "virt", "-bios", "none", "-m", "256", "-cpu", CPU,
        "-global", "virtio-mmio.force-legacy=false",
        "-chardev", "stdio,id=con,mux=on", "-serial", "chardev:con",
        "-mon", "chardev=con,mode=readline", "-nographic", "-no-reboot",
        "-netdev", f"socket,id=n1,listen=127.0.0.1:{PORT}",
        "-device", "virtio-net-device,netdev=n1,bus=virtio-mmio-bus.0",
        "-kernel", elf,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    sock = None
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            sock = socket.create_connection(("127.0.0.1", PORT), timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    if sock is None:
        print(f"[{label}] could not connect to QEMU socket netdev")
        os.killpg(proc.pid, signal.SIGKILL)
        return 2

    log = b""
    sent_untagged = False
    sent_tagged = False
    result = None
    end = time.time() + TIMEOUT

    while time.time() < end:
        ready, _, _ = select.select([proc.stdout, sock], [], [], 0.5)
        if proc.stdout in ready:
            data = os.read(proc.stdout.fileno(), 4096)
            if not data:
                break
            log += data
            sys.stdout.write(data.decode(errors="replace"))
            sys.stdout.flush()

            if not sent_untagged and b"GUEST_READY" in log:
                frame = build_frame(False)
                sock.sendall(struct.pack(">I", len(frame)) + frame)
                sent_untagged = True
            elif sent_untagged and not sent_tagged and b"RX len=1514" in log:
                time.sleep(0.2)
                frame = build_frame(True)
                sock.sendall(struct.pack(">I", len(frame)) + frame)
                sent_tagged = True

            if b"RESULT PASS" in log:
                result = "PASS"
                break
            if b"RESULT FAIL" in log:
                result = "FAIL"
                break
        if sock in ready:
            try:
                sock.recv(4096)
            except OSError:
                pass

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()

    if result is None:
        print(f"[{label}] no RESULT line before timeout; treating as FAIL "
              f"(VLAN frame was not received)")
        result = "FAIL"
    print(f"[{label}] result={result} tagged_sent={sent_tagged}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
