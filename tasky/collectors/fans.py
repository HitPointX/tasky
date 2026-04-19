import ctypes
import struct
import threading
from .base import BaseCollector, make_history

# ── IOKit / SMC bindings ──────────────────────────────────────────────────────

_iokit = ctypes.CDLL('/System/Library/Frameworks/IOKit.framework/IOKit')
_cf    = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')

# mach_task_self_ is a global variable, not a function
_libsys = ctypes.CDLL('libSystem.B.dylib')
_mach_task_self = ctypes.c_uint32.in_dll(_libsys, 'mach_task_self_')

KERN_SUCCESS       = 0
kIOMainPortDefault = 0
KERNEL_INDEX_SMC   = 2
SMC_CMD_READ_INFO  = 9
SMC_CMD_READ_BYTES = 5

# --- SMC data structure ------------------------------------------------------

class _Vers(ctypes.Structure):
    _fields_ = [('major', ctypes.c_uint8), ('minor', ctypes.c_uint8),
                 ('build', ctypes.c_uint8), ('reserved', ctypes.c_uint8),
                 ('release', ctypes.c_uint16)]

class _PLimit(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint16), ('length', ctypes.c_uint16),
                 ('cpuPLimit', ctypes.c_uint32), ('gpuPLimit', ctypes.c_uint32),
                 ('memPLimit', ctypes.c_uint32)]

class _KeyInfo(ctypes.Structure):
    _fields_ = [('dataSize', ctypes.c_uint32), ('dataType', ctypes.c_uint32),
                 ('dataAttributes', ctypes.c_uint8)]

class _SMCKeyData(ctypes.Structure):
    _fields_ = [
        ('key',        ctypes.c_uint32),
        ('vers',       _Vers),
        ('pLimitData', _PLimit),
        ('keyInfo',    _KeyInfo),
        ('result',     ctypes.c_uint8),
        ('status',     ctypes.c_uint8),
        ('data8',      ctypes.c_uint8),
        ('data32',     ctypes.c_uint32),
        ('bytes',      ctypes.c_uint8 * 32),
    ]

_SMCKeyDataPtr = ctypes.POINTER(_SMCKeyData)

# --- IOKit function signatures ------------------------------------------------

_iokit.IOServiceMatching.restype  = ctypes.c_void_p
_iokit.IOServiceMatching.argtypes = [ctypes.c_char_p]

_iokit.IOServiceGetMatchingService.restype  = ctypes.c_uint32
_iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

_iokit.IOServiceOpen.restype  = ctypes.c_int
_iokit.IOServiceOpen.argtypes = [
    ctypes.c_uint32,                  # service
    ctypes.c_uint32,                  # owningTask (mach port)
    ctypes.c_uint32,                  # type
    ctypes.POINTER(ctypes.c_uint32),  # connect (output)
]

_iokit.IOConnectCallStructMethod.restype  = ctypes.c_int
_iokit.IOConnectCallStructMethod.argtypes = [
    ctypes.c_uint32,                       # connection
    ctypes.c_uint32,                       # selector
    _SMCKeyDataPtr,                        # inputStruct
    ctypes.c_size_t,                       # inputStructCnt
    _SMCKeyDataPtr,                        # outputStruct
    ctypes.POINTER(ctypes.c_size_t),       # outputStructCnt
]

_iokit.IOServiceClose.restype  = ctypes.c_int
_iokit.IOServiceClose.argtypes = [ctypes.c_uint32]

_iokit.IOObjectRelease.restype  = ctypes.c_int
_iokit.IOObjectRelease.argtypes = [ctypes.c_uint32]

# ── SMC helper ────────────────────────────────────────────────────────────────

def _k(s: str) -> int:
    return struct.unpack('>I', s.encode())[0]

def _type_str(t: int) -> str:
    return struct.pack('>I', t).decode('ascii', errors='replace')


class _SMC:
    def __init__(self):
        service = _iokit.IOServiceGetMatchingService(
            kIOMainPortDefault,
            _iokit.IOServiceMatching(b'AppleSMC'),
        )
        if not service:
            raise RuntimeError('AppleSMC not found')

        self._conn = ctypes.c_uint32(0)
        ret = _iokit.IOServiceOpen(
            service,
            _mach_task_self.value,
            0,
            ctypes.byref(self._conn),
        )
        _iokit.IOObjectRelease(service)
        if ret != KERN_SUCCESS:
            raise RuntimeError(f'IOServiceOpen failed: {ret:#x}')

    def _call(self, inp: _SMCKeyData):
        out    = _SMCKeyData()
        in_sz  = ctypes.c_size_t(ctypes.sizeof(_SMCKeyData))
        out_sz = ctypes.c_size_t(ctypes.sizeof(_SMCKeyData))
        ret = _iokit.IOConnectCallStructMethod(
            self._conn.value,
            KERNEL_INDEX_SMC,
            ctypes.byref(inp),
            in_sz,
            ctypes.byref(out),
            ctypes.byref(out_sz),
        )
        return out if ret == KERN_SUCCESS else None

    def read(self, key: str):
        """Return (raw_bytes, type_str) or None."""
        inp = _SMCKeyData()
        inp.key   = _k(key)
        inp.data8 = SMC_CMD_READ_INFO
        info = self._call(inp)
        if info is None:
            return None

        inp2 = _SMCKeyData()
        inp2.key              = _k(key)
        inp2.keyInfo.dataSize = info.keyInfo.dataSize
        inp2.data8            = SMC_CMD_READ_BYTES
        result = self._call(inp2)
        if result is None:
            return None

        data = bytes(result.bytes[: info.keyInfo.dataSize])
        return data, _type_str(info.keyInfo.dataType)

    def read_uint8(self, key: str):
        r = self.read(key)
        return r[0][0] if r else None

    def read_float(self, key: str):
        """Read a 4-byte little-endian IEEE 754 float (Apple Silicon SMC fan format)."""
        r = self.read(key)
        if not r:
            return None
        data, typ = r
        if typ.strip() == 'flt' and len(data) >= 4:
            return struct.unpack('<f', data[:4])[0]
        # Fallback: fpe2 big-endian fixed-point (Intel SMC format)
        if len(data) >= 2:
            return struct.unpack('>H', data[:2])[0] / 4.0
        return None

    def close(self):
        _iokit.IOServiceClose(self._conn.value)


# ── Public probe ──────────────────────────────────────────────────────────────

def read_fans_smc():
    """Read fan RPMs directly via IOKit — no sudo required."""
    try:
        smc   = _SMC()
        count = smc.read_uint8('FNum') or 0
        fans  = []
        for i in range(count):
            rpm     = smc.read_float(f'F{i}Ac')
            min_rpm = smc.read_float(f'F{i}Mn') or 0.0
            max_rpm = smc.read_float(f'F{i}Mx') or 6000.0
            if rpm is not None:
                fans.append({
                    'id':      i,
                    'label':   f'Fan {i}',
                    'rpm':     rpm,
                    'min_rpm': min_rpm,
                    'max_rpm': max_rpm,
                })
        smc.close()
        return fans
    except Exception:
        return []


# ── Collector ─────────────────────────────────────────────────────────────────

class FanCollector(BaseCollector):
    def __init__(self, interval=2.0, **_):
        super().__init__(interval)
        self._histories = {}

    def collect(self):
        fans = read_fans_smc()
        for fan in fans:
            fid = fan['id']
            if fid not in self._histories:
                self._histories[fid] = make_history()
            self._histories[fid].append(fan['rpm'])
            fan['history'] = list(self._histories[fid])

        return {
            'fans':      fans,
            'has_fans':  len(fans) > 0,
            'needs_sudo': False,
        }
