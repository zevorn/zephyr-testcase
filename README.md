# zephyr-testcase

Zephyr test cases. Each test lives in its own directory with its own justfile,
README, and test sources.

## Tests

### virtio-net-vlan-test

Verifies that the Zephyr virtio-net driver can receive a full 1518-byte
VLAN-tagged frame when CONFIG_NET_VLAN is enabled. It corresponds to Zephyr
patch fd64c2f22d3f ("fix frame buffer size for tagged frames").

See virtio-net-vlan-test/README.md for details.

Quick start:

    cd virtio-net-vlan-test
    just doctor
    just test

Build artifacts (build/) and the upstream/main snapshot (baseline/) are created
inside the test directory and are gitignored.
