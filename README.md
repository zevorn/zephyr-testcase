# zephyr-testcase

Zephyr test cases. Each test lives in its own directory with its own justfile,
README, and test sources.

## Tests

### virtio-net-vlan-test

Verifies that the Zephyr virtio-net driver can receive a full 1518-byte
VLAN-tagged frame when CONFIG_NET_VLAN is enabled. It corresponds to Zephyr
patch 49dfc3e50952 ("fix frame buffer size for tagged frames").

See virtio-net-vlan-test/README.md for details.

### virtio-net-tx-overrun-test

Verifies that the Zephyr virtio-net driver rejects frames that do not fit into
its TX buffer. It corresponds to Zephyr PR #122791 ("fix TX buffer overrun for
oversized frames") and issue #122790.

See virtio-net-tx-overrun-test/README.md for details.

## Quick start

    cd virtio-net-vlan-test
    just doctor
    just test

    cd ../virtio-net-tx-overrun-test
    ZEPHYR_BASE=../../zephyr-virtio-tx just doctor
    ZEPHYR_BASE=../../zephyr-virtio-tx just test

Build artifacts (build/) and the upstream/main snapshot (baseline/) are created
inside each test directory and are gitignored.
