import psutil
import subprocess
import platform
import time
import os
from .base import BaseCollector, make_history


def _cpu_brand():
    try:
        return subprocess.check_output(
            ['sysctl', '-n', 'machdep.cpu.brand_string'],
            text=True, timeout=2
        ).strip()
    except Exception:
        return platform.processor() or 'Unknown CPU'


class CPUCollector(BaseCollector):
    def __init__(self, interval=1.0):
        super().__init__(interval)
        self._cpu_history = make_history()
        self._brand = _cpu_brand()
        self._cpu_count_phys = psutil.cpu_count(logical=False) or 1
        self._cpu_count_logic = psutil.cpu_count(logical=True) or 1
        self._mem_total = psutil.virtual_memory().total  # never changes
        self._boot_time = psutil.boot_time()             # never changes
        self._proc_tick = 0   # process list refreshes every other tick
        self._cached_procs = []
        # Prime psutil counters so first reading isn't 0
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)

    def _refresh_processes(self):
        procs = []
        for proc in psutil.process_iter(
            ['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'cmdline']
        ):
            try:
                info = proc.info
                info['cpu_percent']    = info['cpu_percent']    or 0.0
                info['memory_percent'] = info['memory_percent'] or 0.0
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda p: p['cpu_percent'], reverse=True)
        self._cached_procs = procs[:25]

    def collect(self):
        cpu_pct = psutil.cpu_percent(interval=None)
        core_pcts = psutil.cpu_percent(interval=None, percpu=True)
        self._cpu_history.append(cpu_pct)

        mem = psutil.virtual_memory()

        try:
            freq = psutil.cpu_freq()
            freq_mhz = freq.current if freq else 0
        except Exception:
            freq_mhz = 0

        try:
            load = psutil.getloadavg()
        except Exception:
            load = (0.0, 0.0, 0.0)

        # Refresh process list every other tick (2s effective interval)
        self._proc_tick += 1
        if self._proc_tick % 2 == 0:
            self._refresh_processes()

        return {
            'cpu_pct':          cpu_pct,
            'cpu_history':      list(self._cpu_history),
            'core_pcts':        core_pcts,
            'load':             load,
            'freq_mhz':         freq_mhz,
            'processes':        self._cached_procs,
            'cpu_count_phys':   self._cpu_count_phys,
            'cpu_count_logic':  self._cpu_count_logic,
            'brand':            self._brand,
            'mem_total':        self._mem_total,
            'mem_used':         mem.used,
            'mem_pct':          mem.percent,
            'uptime_s':         time.time() - self._boot_time,
        }
