import curses
import time
import os
import signal

from .collectors.cpu import CPUCollector
from .collectors.network import NetworkCollector
from .collectors.gpu import GPUCollector
from .collectors.fans import FanCollector
from .ui import colors
from .ui import views

REFRESH_RATE   = 1.0
NUM_TABS       = 4
SEL_TIMEOUT    = 60.0   # seconds before auto-deselect


class App:
    def __init__(self):
        self.tab         = 0
        self.collectors  = {}
        self.running     = False

        # Process selection
        self.sel_pid      = None    # PID of selected process (None = no selection)
        self.sel_time     = None    # monotonic time of last nav action
        self.proc_scroll  = 0       # top-of-list scroll offset

        # Kill confirmation overlay
        self.kill_active  = False   # dialog visible
        self.kill_yes     = False   # True = YES highlighted, False = NO
        self.kill_pid     = None
        self.kill_name    = ''

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def _setup(self):
        self.collectors['cpu'] = CPUCollector(interval=REFRESH_RATE)
        self.collectors['net'] = NetworkCollector(interval=REFRESH_RATE)
        self.collectors['gpu'] = GPUCollector(interval=3.0)
        self.collectors['fan'] = FanCollector(interval=2.0)
        for c in self.collectors.values():
            c.start()

    def _teardown(self):
        for c in self.collectors.values():
            c.stop()

    def run(self, stdscr):
        colors.init()
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(250)

        self._setup()
        self.running  = True
        last_render   = 0.0

        try:
            while self.running:
                key = stdscr.getch()
                if key != -1:
                    self._handle_key(key)

                now = time.monotonic()

                # Auto-deselect after SEL_TIMEOUT seconds of inactivity
                if (self.sel_pid is not None
                        and not self.kill_active
                        and self.sel_time is not None
                        and now - self.sel_time > SEL_TIMEOUT):
                    self._clear_selection()

                if now - last_render >= REFRESH_RATE:
                    last_render = now
                    self._render(stdscr)
        finally:
            self._teardown()

    # ── key handling ──────────────────────────────────────────────────────────

    def _handle_key(self, key):
        # Kill confirmation dialog eats all keys
        if self.kill_active:
            self._handle_kill_key(key)
            return

        # CPU-tab navigation
        if self.tab == 0:
            if key == curses.KEY_UP:
                self._proc_nav(-1)
                return
            if key == curses.KEY_DOWN:
                self._proc_nav(+1)
                return
            if key in (ord('k'), ord('K')) and self.sel_pid is not None:
                self._start_kill()
                return
            if key == 27:               # ESC clears selection
                self._clear_selection()
                return

        # Tab switching
        if key in (ord('q'), ord('Q')):
            self.running = False
        elif key in (curses.KEY_RIGHT, ord('\t'), ord('l')):
            self._clear_selection()
            self.tab = (self.tab + 1) % NUM_TABS
        elif key in (curses.KEY_LEFT, ord('h')):
            self._clear_selection()
            self.tab = (self.tab - 1) % NUM_TABS
        elif key == ord('1'):
            self._clear_selection(); self.tab = 0
        elif key == ord('2'):
            self._clear_selection(); self.tab = 1
        elif key == ord('3'):
            self._clear_selection(); self.tab = 2
        elif key == ord('4'):
            self._clear_selection(); self.tab = 3

    def _handle_kill_key(self, key):
        if key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            self.kill_yes = not self.kill_yes
        elif key in (ord('\n'), ord('\r'), 10, 13):
            if self.kill_yes:
                self._do_kill()
            self._clear_selection()
        elif key in (27, ord('q'), ord('Q')):   # ESC / q cancel
            self._clear_selection()

    # ── process navigation ────────────────────────────────────────────────────

    def _proc_nav(self, direction):
        procs = self.collectors['cpu'].get_data().get('processes', [])
        if not procs:
            return

        self.sel_time = time.monotonic()

        if self.sel_pid is None:
            # First key press: spawn at top (UP) or bottom (DOWN)
            if direction == -1:
                self.sel_pid = procs[0]['pid']
                self.proc_scroll = 0
            else:
                self.sel_pid = procs[-1]['pid']
                self.proc_scroll = max(0, len(procs) - 1)
            return

        # Find current index
        idx = next((i for i, p in enumerate(procs) if p.get('pid') == self.sel_pid), None)
        if idx is None:
            self.sel_pid = procs[0]['pid']
            self.proc_scroll = 0
            return

        new_idx = max(0, min(len(procs) - 1, idx + direction))
        self.sel_pid = procs[new_idx]['pid']

        # Adjust scroll so selection stays visible
        visible = self._visible_proc_rows()
        if new_idx < self.proc_scroll:
            self.proc_scroll = new_idx
        elif new_idx >= self.proc_scroll + visible:
            self.proc_scroll = new_idx - visible + 1

    def _visible_proc_rows(self):
        """Estimate how many process rows fit on screen (conservative)."""
        try:
            h = self.collectors['cpu']._screen_h
        except AttributeError:
            h = 40
        return max(5, h - 13)

    # ── kill ──────────────────────────────────────────────────────────────────

    def _start_kill(self):
        procs = self.collectors['cpu'].get_data().get('processes', [])
        target = next((p for p in procs if p.get('pid') == self.sel_pid), None)
        if target is None:
            return
        self.kill_active = True
        self.kill_yes    = False
        self.kill_pid    = self.sel_pid
        self.kill_name   = (target.get('name') or '')[:30]

    def _do_kill(self):
        if self.kill_pid is None:
            return
        try:
            os.kill(self.kill_pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    def _clear_selection(self):
        self.sel_pid     = None
        self.sel_time    = None
        self.proc_scroll = 0
        self.kill_active = False
        self.kill_yes    = False
        self.kill_pid    = None
        self.kill_name   = ''

    # ── render ────────────────────────────────────────────────────────────────

    def _render(self, stdscr):
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        # Store for visible-rows calculation
        self.collectors['cpu']._screen_h = h

        views.draw_header(stdscr, w)
        views.draw_tabs(stdscr, w, self.tab)

        try:
            if self.tab == 0:
                views.draw_cpu(stdscr, h, w, self.collectors['cpu'],
                               sel_pid=self.sel_pid,
                               scroll=self.proc_scroll)
            elif self.tab == 1:
                views.draw_network(stdscr, h, w, self.collectors['net'])
            elif self.tab == 2:
                views.draw_gpu(stdscr, h, w, self.collectors['gpu'])
            elif self.tab == 3:
                views.draw_fans(stdscr, h, w, self.collectors['fan'])
        except Exception as e:
            views._w(stdscr, 4, 2, f'Render error: {e}'[:w - 4],
                     curses.color_pair(3) | curses.A_BOLD)

        if self.kill_active:
            views.draw_kill_confirm(stdscr, h, w,
                                    self.kill_pid, self.kill_name,
                                    self.kill_yes)

        views.draw_footer(stdscr, h, w)
        stdscr.refresh()
