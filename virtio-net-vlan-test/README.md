# virtio-net VLAN RX test

Verifies that the Zephyr virtio-net driver can receive a full 1518-byte
VLAN-tagged frame when CONFIG_NET_VLAN is enabled. Corresponds to Zephyr patch
fd64c2f22d3f ("fix frame buffer size for tagged frames").

Everything is managed by the justfile in this directory.

## Layout

    virtio-net-vlan-test/
      justfile         test management (build / test / QEMU / before-after)
      CMakeLists.txt   Zephyr application
      prj.conf         CONFIG_NET_VLAN=y and AF_PACKET configuration
      src/main.c       guest side: raw AF_PACKET RX, prints length, PASS on 1518
      host.py          automated test: start QEMU, inject frames, assert
      inject.py        manual test: inject one frame into a running QEMU
      build/           build artifacts (gitignored)
      baseline/        upstream/main snapshot (gitignored)

## Requirements

- A Zephyr tree: defaults to ../../zephyr-virtio, override with ZEPHYR_BASE
- Zephyr SDK: discovered automatically by CMake (here: ~/.tools/zephyr-sdk-1.0.1)
- cmake, ninja, python3 (Zephyr build requirements)
- qemu-system-riscv64: use the homebrew build; the QEMU shipped with the SDK
  lacks the socket networking backend used by this test

## Quick start

    cd zephyr-testcase/virtio-net-vlan-test
    just doctor          # check dependencies
    just build           # build against ../../zephyr-virtio
    just test            # build + start QEMU + inject frames + assert PASS
    just demo            # before/after: patched tree PASS, upstream/main FAIL

## Recipes

    just                 # list all recipes
    just info            # show paths and tools in use
    just doctor          # check dependencies
    just build           # build against the current ZEPHYR_BASE tree
    just build-tree DIR  # build against an arbitrary Zephyr tree
    just test            # end-to-end test (expects PASS)
    just test-tree DIR   # end-to-end test against an arbitrary Zephyr tree
    just baseline        # export upstream/main into baseline/
    just test-before     # test upstream/main (expects FAIL, reproduces the bug)
    just demo            # current tree PASS + upstream/main FAIL, one shot
    just qemu            # start QEMU in the foreground
    just inject          # inject one plain 1514B frame (manual flow)
    just inject-vlan     # inject one VLAN-tagged 1518B frame (manual flow)
    just clean           # remove build/ and baseline/

## Manual debugging

Terminal 1:

    just qemu

Terminal 2, within 60 seconds after the guest prints GUEST_READY:

    just inject-vlan

The guest prints the length of every received frame; receiving a 1518-byte
VLAN frame means the fix is effective.

## How the test works

1. The guest app opens a raw AF_PACKET / ETH_P_ALL socket. Zephyr delivers the
   raw L2 frame to packet sockets before the Ethernet L2 processes it, so the
   test does not depend on any VLAN interface configuration.
2. host.py uses QEMU's socket netdev as a raw Ethernet channel. It first
   injects a 1514-byte plain frame (control), then a 1518-byte VLAN frame
   (VLAN 100, inner ethertype 0x0800).
3. The guest prints RESULT PASS when the 1518-byte frame is received, or
   RESULT FAIL on timeout.
4. On unmodified upstream/main the RX buffer is only 1526 bytes, while the
   tagged frame needs 12 + 1518 = 1530 bytes, so the device drops it and the
   test FAILs. That is exactly the bug being reproduced.

## Environment variables

    ZEPHYR_BASE   Zephyr tree path (default: ../../zephyr-virtio)
    PYTHON        python interpreter for host.py/inject.py (default: python3)
    QEMU          qemu-system-riscv64 binary
    VNET_PORT     QEMU socket netdev port (default: 45987)
    BOARD         default: qemu_riscv64
