/*
 * Scratch VLAN RX test: a virtio-net device receives an injected 1518-byte
 * VLAN-tagged frame. A raw AF_PACKET socket sees the L2 frame before the
 * Ethernet L2 processes it, so the size is observed independently of any
 * VLAN interface configuration.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include <zephyr/kernel.h>
#include <zephyr/net/socket.h>
#include <zephyr/net/net_if.h>
#include <zephyr/net/net_ip.h>
#include <zephyr/net/ethernet.h>

static uint8_t rx_buf[2048];

int main(void)
{
	struct net_if *iface = net_if_get_first_by_type(&NET_L2_GET_NAME(ETHERNET));
	struct net_sockaddr_ll addr = {0};
	struct zsock_pollfd pfd;
	bool got_1514 = false;
	bool got_1518 = false;
	int sock;
	int ret;
	int len;

	if (iface == NULL) {
		printk("RESULT FAIL no-ethernet-iface\n");
		return 1;
	}

	net_if_up(iface);
	k_sleep(K_MSEC(200));

	sock = zsock_socket(NET_AF_PACKET, NET_SOCK_RAW, net_htons(ETH_P_ALL));
	if (sock < 0) {
		printk("RESULT FAIL socket=%d\n", -errno);
		return 1;
	}

	addr.sll_family = NET_AF_PACKET;
	addr.sll_protocol = net_htons(ETH_P_ALL);
	addr.sll_ifindex = net_if_get_by_iface(iface);

	if (zsock_bind(sock, (struct net_sockaddr *)&addr, sizeof(addr)) < 0) {
		printk("RESULT FAIL bind=%d\n", -errno);
		return 1;
	}

	printk("GUEST_READY iface=%d\n", net_if_get_by_iface(iface));

	pfd.fd = sock;
	pfd.events = ZSOCK_POLLIN;
	pfd.revents = 0;

	/* Keep a 60 s window for manual injection; the automated host.py run ends in 30 s */
	for (int i = 0; i < 60; i++) {
		ret = zsock_poll(&pfd, 1, 1000);
		if (ret == 0) {
			continue;
		}
		if (ret < 0) {
			printk("RESULT FAIL poll=%d\n", -errno);
			return 1;
		}

		len = zsock_recv(sock, rx_buf, sizeof(rx_buf), 0);
		if (len < 0) {
			printk("RESULT FAIL recv=%d\n", -errno);
			return 1;
		}

		printk("RX len=%d", len);
		if (len >= 18 && rx_buf[12] == 0x81 && rx_buf[13] == 0x00) {
			printk(" vlan_tci=0x%02x%02x inner=0x%02x%02x",
			       rx_buf[14], rx_buf[15], rx_buf[16], rx_buf[17]);
		}
		printk("\n");

		if (len == 1514) {
			got_1514 = true;
		}
		if (len == 1518) {
			got_1518 = true;
			break;
		}
	}

	printk("RESULT %s untagged_1514=%d tagged_1518=%d\n",
	       got_1518 ? "PASS" : "FAIL", got_1514, got_1518);

	return got_1518 ? 0 : 1;
}
