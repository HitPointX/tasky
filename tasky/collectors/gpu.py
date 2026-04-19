import subprocess
import re
import json
from .base import BaseCollector, make_history


def _get_gpu_name():
    try:
        out = subprocess.check_output(
            ['system_profiler', 'SPDisplaysDataType', '-json'],
            text=True, timeout=5
        )
        data = json.loads(out)
        displays = data.get('SPDisplaysDataType', [])
        if displays:
            return displays[0].get('sppci_model', 'Unknown GPU')
    except Exception:
        pass
    return 'Apple Silicon GPU'


def _parse_ioreg_gpu():
    try:
        out = subprocess.check_output(
            ['ioreg', '-r', '-c', 'IOAccelerator', '-d', '3'],
            text=True, timeout=3
        )
    except Exception:
        return {}

    result = {}
    perf = re.search(r'"PerformanceStatistics"\s*=\s*\{([^}]+)\}', out)
    if perf:
        s = perf.group(1)
        for key, dest in (
            (r'"Device Utilization %"\s*=\s*(\d+)',   'utilization'),
            (r'"Renderer Utilization %"\s*=\s*(\d+)', 'renderer_util'),
            (r'"Tiler Utilization %"\s*=\s*(\d+)',    'tiler_util'),
        ):
            m = re.search(key, s)
            if m:
                result[dest] = int(m.group(1))

    m = re.search(r'"VRAM,totalMB"\s*=\s*(\d+)', out)
    if m:
        result['vram_total_mb'] = int(m.group(1))

    m = re.search(r'"VRAM,currentMB"\s*=\s*(\d+)', out)
    if m:
        result['vram_used_mb'] = int(m.group(1))
    elif 'vram_used_mb' not in result:
        m = re.search(r'"inUseVRAMBytes"\s*=\s*(\d+)', out)
        if m:
            result['vram_used_mb'] = int(m.group(1)) // (1024 * 1024)

    return result


class GPUCollector(BaseCollector):
    def __init__(self, interval=3.0):
        super().__init__(interval)
        self._util_history = make_history()
        self._gpu_name = _get_gpu_name()
        self._vram_total_mb = None   # cached after first successful read

    def collect(self):
        info = _parse_ioreg_gpu()
        util = info.get('utilization', 0)
        self._util_history.append(float(util))

        # Cache VRAM total — it never changes at runtime
        if self._vram_total_mb is None and 'vram_total_mb' in info:
            self._vram_total_mb = info['vram_total_mb']

        return {
            'name':          self._gpu_name,
            'utilization':   util,
            'renderer_util': info.get('renderer_util', 0),
            'tiler_util':    info.get('tiler_util', 0),
            'vram_total_mb': self._vram_total_mb or info.get('vram_total_mb', 0),
            'vram_used_mb':  info.get('vram_used_mb', 0),
            'util_history':  list(self._util_history),
            'available':     bool(info),
        }
