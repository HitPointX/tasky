import collections
import curses
import math

_NORMAL = 'normal'
_DIZZY  = 'dizzy'
_BLINK  = 'blink'

_DIZZY_SPEED = 280   # cumulative cells/sec (needs wild movement to trigger)
_DIZZY_DUR   = 3.0   # seconds of dizziness
_BLINK_DUR   = 0.45  # seconds for the blink
_ANIM_STEP   = 0.12  # seconds per dizzy animation frame
_SAMPLE_RATE = 0.10  # seconds between speed samples
_H_ZONE      = 4     # cols from eye center before pupil shifts

_EYE_LEFT   = '(●  )'
_EYE_CENTER = '( ● )'
_EYE_RIGHT  = '(  ●)'
_EYE_BLINK  = '( _ )'
_EYE_GAP    = 1

_DIZZY_FRAMES = ['( @ )', '( ~ )', '( * )', '( ~ )']


class GooglyEyes:
    def __init__(self):
        self._mx    = -1
        self._my    = -1
        self._state = _NORMAL
        self._dizzy_until  = 0.0
        self._blink_until  = 0.0
        self._frame        = 0
        self._frame_t      = 0.0
        self._sample_t     = 0.0
        self._history      = collections.deque()  # (x, y) sampled every _SAMPLE_RATE s

    # ── public ────────────────────────────────────────────────────────────────

    def update(self, x, y):
        """Store latest mouse position. O(1) — called on every raw mouse event."""
        self._mx, self._my = x, y

    def tick(self, t):
        """Drive state machine and periodic speed sampling. Called from main loop."""
        # Animation state transitions (cheap, always runs)
        if self._state == _DIZZY:
            if t >= self._dizzy_until:
                self._state = _BLINK
                self._blink_until = t + _BLINK_DUR
            elif t - self._frame_t >= _ANIM_STEP:
                self._frame = (self._frame + 1) % len(_DIZZY_FRAMES)
                self._frame_t = t
            return  # no speed check needed while dizzy

        if self._state == _BLINK:
            if t >= self._blink_until:
                self._state = _NORMAL
            return

        # Normal: sample position & check speed at _SAMPLE_RATE intervals only
        if t - self._sample_t < _SAMPLE_RATE:
            return
        self._sample_t = t

        if self._mx < 0:
            return
        self._history.append((self._mx, self._my, t))
        cutoff = t - 0.5
        while self._history and self._history[0][2] < cutoff:
            self._history.popleft()

        if self._speed() > _DIZZY_SPEED:
            self._history.clear()
            self._state = _DIZZY
            self._dizzy_until = t + _DIZZY_DUR
            self._frame = 0
            self._frame_t = t

    @property
    def animating(self):
        return self._state in (_DIZZY, _BLINK)

    def draw(self, screen, h, w):
        """Render eyes. Pure output — no state changes."""
        if h < 1 or w < 15:
            return
        self._render(screen, w)

    # ── internal ──────────────────────────────────────────────────────────────

    def _speed(self):
        if len(self._history) < 2:
            return 0.0
        dt = self._history[-1][2] - self._history[0][2]
        if dt < 0.05:
            return 0.0
        total = 0.0
        for i in range(1, len(self._history)):
            x0, y0, _ = self._history[i - 1]
            x1, y1, _ = self._history[i]
            dx = (x1 - x0) * 0.5  # account for terminal cell aspect ratio
            dy = y1 - y0
            total += math.hypot(dx, dy)
        return total / dt

    def _render(self, screen, w):
        eye_w = 5
        total = eye_w * 2 + _EYE_GAP
        lx = (w - total) // 2
        rx = lx + eye_w + _EYE_GAP
        attr = curses.color_pair(7) | curses.A_BOLD  # white on blue, matches header

        if self._state == _BLINK:
            self._put(screen, 0, lx, _EYE_BLINK, attr)
            self._put(screen, 0, rx, _EYE_BLINK, attr)
        elif self._state == _DIZZY:
            frame = _DIZZY_FRAMES[self._frame]
            self._put(screen, 0, lx, frame, attr)
            self._put(screen, 0, rx, frame, attr)
        else:
            self._put(screen, 0, lx, self._look(lx + 2), attr)
            self._put(screen, 0, rx, self._look(rx + 2), attr)

    def _look(self, eye_cx):
        if self._mx < 0:
            return _EYE_CENTER
        dx = self._mx - eye_cx
        if dx < -_H_ZONE:
            return _EYE_LEFT
        if dx > _H_ZONE:
            return _EYE_RIGHT
        return _EYE_CENTER

    def _put(self, screen, y, x, text, attr):
        h, w = screen.getmaxyx()
        if y < 0 or y >= h or x < 0 or x + len(text) > w:
            return
        try:
            screen.addstr(y, x, text, attr)
        except curses.error:
            pass
