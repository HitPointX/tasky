import psutil
import time
from .base import BaseCollector, make_history


class NetworkCollector(BaseCollector):
    def __init__(self, interval=1.0):
        super().__init__(interval)
        self._prev_counters = {}
        self._prev_time = time.monotonic()
        self._rx_histories = {}
        self._tx_histories = {}
        # Prime
        self._prev_counters = psutil.net_io_counters(pernic=True)

    def collect(self):
        now = time.monotonic()
        dt = now - self._prev_time
        self._prev_time = now

        counters = psutil.net_io_counters(pernic=True)
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        interfaces = []
        for nic, cur in counters.items():
            prev = self._prev_counters.get(nic)
            if prev is None:
                rx_rate = 0.0
                tx_rate = 0.0
            else:
                rx_rate = max(0.0, (cur.bytes_recv - prev.bytes_recv) / dt)
                tx_rate = max(0.0, (cur.bytes_sent - prev.bytes_sent) / dt)

            if nic not in self._rx_histories:
                self._rx_histories[nic] = make_history()
                self._tx_histories[nic] = make_history()

            self._rx_histories[nic].append(rx_rate)
            self._tx_histories[nic].append(tx_rate)

            ipv4 = ''
            for addr in addrs.get(nic, []):
                if addr.family.name == 'AF_INET':
                    ipv4 = addr.address
                    break

            is_up = stats[nic].isup if nic in stats else False

            interfaces.append({
                'name': nic,
                'ipv4': ipv4,
                'rx_rate': rx_rate,
                'tx_rate': tx_rate,
                'rx_total': cur.bytes_recv,
                'tx_total': cur.bytes_sent,
                'rx_history': list(self._rx_histories[nic]),
                'tx_history': list(self._tx_histories[nic]),
                'is_up': is_up,
            })

        self._prev_counters = counters

        interfaces.sort(key=lambda i: (not i['is_up'], i['name']))
        return {'interfaces': interfaces}
