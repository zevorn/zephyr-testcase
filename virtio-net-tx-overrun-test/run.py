#!/usr/bin/env python3
"""Run the virtio-net TX length test under QEMU and report PASS/FAIL.

The guest sends 64, 1514, 1515 and 2000-byte frames through the driver and
prints a RESULT line. No host-side frame injection is needed: QEMU only needs
a virtio-net device (with an arbitrary network backend) for the driver to
bind.

Usage: run.py <zephyr.elf> [label]
"""
import os
import select
import signal
import subprocess
import sys
import time

QEMU = os.environ.get("QEMU", "qemu-system-riscv64")
CPU = os.environ.get(
    "QEMU_CPU",
    "rv64i,i=on,m=on,a=on,f=on,d=on,c=on,zicsr=on,zifencei=on,zicntr=on,zkr=on,pmp=on,u=on",
)
TIMEOUT = float(os.environ.get("VNET_TIMEOUT", "30"))


def main():
    elf = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(os.path.dirname(elf))

    cmd = [
        QEMU, "-machine", "virt", "-bios", "none", "-m", "256", "-cpu", CPU,
        "-global", "virtio-mmio.force-legacy=false",
        "-chardev", "stdio,id=con,mux=on", "-serial", "chardev:con",
        "-mon", "chardev=con,mode=readline", "-nographic", "-no-reboot",
        "-netdev", "user,id=n1",
        "-device", "virtio-net-device,netdev=n1,bus=virtio-mmio-bus.0",
        "-kernel", elf,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    log = b""
    result = None
    end = time.time() + TIMEOUT

    while time.time() < end:
        ready, _, _ = select.select([proc.stdout], [], [], 0.5)
        if proc.stdout in ready:
            data = os.read(proc.stdout.fileno(), 4096)
            if not data:
                break
            log += data
            sys.stdout.write(data.decode(errors="replace"))
            sys.stdout.flush()

            if b"RESULT PASS" in log:
                result = "PASS"
                break
            if b"RESULT FAIL" in log:
                result = "FAIL"
                break

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()

    if result is None:
        print(f"[{label}] no RESULT line before timeout; treating as FAIL")
        result = "FAIL"

    print(f"[{label}] result={result}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
