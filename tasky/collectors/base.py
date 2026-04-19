import threading
from collections import deque

HISTORY_LEN = 60


class BaseCollector:
    def __init__(self, interval=1.0):
        self.interval = interval
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._data = {}

    def collect(self):
        return {}

    def get_data(self):
        with self._lock:
            return dict(self._data)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                data = self.collect()
                with self._lock:
                    self._data = data
            except Exception:
                pass
            self._stop_event.wait(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)


def make_history(length=HISTORY_LEN):
    return deque([0.0] * length, maxlen=length)
