/*
 * virtio-net TX length test: sends frames of several sizes through the
 * driver and checks that frames larger than the TX buffer are rejected.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include <errno.h>
#include <zephyr/kernel.h>
#include <zephyr/net/net_if.h>
#include <zephyr/net/net_l2.h>
#include <zephyr/net/net_pkt.h>
#include <zephyr/net/ethernet.h>

static int send_frame(const struct device *dev, size_t len)
{
	const struct ethernet_api *api = (const struct ethernet_api *)dev->api;
	struct net_pkt *pkt;
	int ret;

	/*
	 * Allocate without an iface: net_pkt_alloc_with_buffer() caps a packet
	 * on an Ethernet iface at NET_ETH_MAX_FRAME_SIZE, which would prevent
	 * the oversized frames this test feeds to the driver.
	 */
	pkt = net_pkt_alloc_with_buffer(NULL, len, NET_AF_UNSPEC, 0, K_FOREVER);
	if (pkt == NULL) {
		printk("SEND len=%u alloc failed\n", (unsigned int)len);
		return -ENOMEM;
	}

	ret = net_pkt_memset(pkt, 0xa5, len);
	if (ret != 0) {
		printk("SEND len=%u fill failed ret=%d\n", (unsigned int)len, ret);
		net_pkt_unref(pkt);
		return -EIO;
	}

	net_pkt_cursor_init(pkt);
	ret = api->send(dev, pkt);
	printk("SEND len=%u ret=%d\n", (unsigned int)len, ret);
	net_pkt_unref(pkt);

	return ret;
}

int main(void)
{
	struct net_if *iface;
	const struct device *dev;
	bool pass = true;

	printk("TX_OVERRUN start\n");

	iface = net_if_get_first_by_type(&NET_L2_GET_NAME(ETHERNET));
	if (iface == NULL) {
		printk("TX_OVERRUN no ethernet interface\n");
		printk("RESULT FAIL\n");
		return 1;
	}

	dev = net_if_get_device(iface);
	printk("TX_OVERRUN dev=%s ready=%d\n", dev->name, device_is_ready(dev));
	if (!device_is_ready(dev)) {
		printk("TX_OVERRUN device not ready\n");
		printk("RESULT FAIL\n");
		return 1;
	}

	net_if_up(iface);
	k_sleep(K_MSEC(100));

	if (send_frame(dev, 64U) != 0) {
		pass = false;
	}

	if (send_frame(dev, 1514U) != 0) {
		pass = false;
	}

	if (send_frame(dev, 1515U) != -EMSGSIZE) {
		pass = false;
	}

	if (send_frame(dev, 2000U) != -EMSGSIZE) {
		pass = false;
	}

	printk("RESULT %s\n", pass ? "PASS" : "FAIL");

	return pass ? 0 : 1;
}
