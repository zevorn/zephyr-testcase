# virtio-net TX overrun test

Checks that the Zephyr virtio-net driver rejects frames that do not fit into
its TX buffer instead of copying them past the end of the buffer.

Corresponds to Zephyr PR #122791 ("drivers: ethernet: virtio: fix TX buffer
overrun for oversized frames") and issue #122790.

## What it does

The guest app takes the first Ethernet interface, obtains the driver's
ethernet_api, and calls send() with four frames: 64, 1514, 1515 and 2000 bytes.

- 64 and 1514 bytes must be accepted (return 0).
- 1515 and 2000 bytes must be rejected with -EMSGSIZE.

On upstream/main without the fix the driver copies the oversized frames into
the 1526-byte TX buffer without checking the length, so send() returns 0 and
the test prints RESULT FAIL. With the fix the oversized frames are rejected
and the test prints RESULT PASS.

No host-side frame injection is needed; QEMU only needs a virtio-net device
with a network backend for the driver to bind.

## Layout

    run.py          start QEMU, wait for the RESULT line, exit 0/1
    src/main.c      guest app that drives the TX path
    prj.conf        networking + virtio-net, no sockets needed
    CMakeLists.txt  Zephyr application build
    justfile        build/run recipes

## Requirements

- Zephyr worktree with the TX fix, for example ZEPHYR_BASE=../../zephyr-virtio-tx
- Zephyr SDK, cmake, ninja
- homebrew qemu-system-riscv64 (the SDK QEMU build lacks the userspace
  networking backend used to create the virtio-net device)
- python3 (standard library only)

## Quick start

    cd virtio-net-tx-overrun-test
    just doctor
    ZEPHYR_BASE=../../zephyr-virtio-tx just test         # expect PASS
    ZEPHYR_BASE=../../zephyr-virtio-tx just test-before  # expect FAIL (bug reproduced)

The baseline is exported from upstream/main with git archive into baseline/,
built, and run: it must print RESULT FAIL, proving that the test catches the
bug.

## Recipes

    just info           show paths and tools
    just doctor         check dependencies
    just build          build the app against ZEPHYR_BASE
    just test           build + run + assert PASS
    just test-before    build upstream/main + assert FAIL (bug reproduced)
    just demo           both of the above
    just qemu           run QEMU manually (Ctrl-a x to quit)
    just clean          remove build/ and baseline/

Environment variables: ZEPHYR_BASE (tree under test), QEMU, QEMU_CPU, BOARD,
PYTHON, VNET_TIMEOUT.
