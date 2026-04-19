import curses


class C:
    GOOD = 1       # green
    WARN = 2       # yellow
    CRIT = 3       # red
    BORDER = 4     # cyan
    TAB_SEL = 5    # white on blue (selected tab)
    TAB_UNSEL = 6  # cyan on black (unselected tab)
    HEADER = 7     # bold white on blue (title bar)
    DIM = 8        # dark grey
    BLUE = 9       # blue (rx graph)
    MAGENTA = 10   # magenta (tx graph)
    WHITE = 11     # plain white
    SEL_PROC = 12  # selected process row (baby blue bg)
    CONFIRM_YES = 13
    CONFIRM_NO  = 14


def init():
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(C.GOOD,     curses.COLOR_GREEN,   -1)
    curses.init_pair(C.WARN,     curses.COLOR_YELLOW,  -1)
    curses.init_pair(C.CRIT,     curses.COLOR_RED,     -1)
    curses.init_pair(C.BORDER,   curses.COLOR_CYAN,    -1)
    curses.init_pair(C.TAB_SEL,  curses.COLOR_WHITE,   curses.COLOR_BLUE)
    curses.init_pair(C.TAB_UNSEL, curses.COLOR_CYAN,   -1)
    curses.init_pair(C.HEADER,   curses.COLOR_WHITE,   curses.COLOR_BLUE)
    curses.init_pair(C.DIM,      curses.COLOR_BLACK,   -1)
    curses.init_pair(C.BLUE,     curses.COLOR_BLUE,    -1)
    curses.init_pair(C.MAGENTA,  curses.COLOR_MAGENTA, -1)
    curses.init_pair(C.WHITE,    curses.COLOR_WHITE,   -1)

    # Baby blue selection highlight — use 256-colour index 153 if available
    if curses.COLORS >= 256:
        curses.init_pair(C.SEL_PROC,   curses.COLOR_BLACK, 153)
        curses.init_pair(C.CONFIRM_YES, curses.COLOR_BLACK, 153)
    else:
        curses.init_pair(C.SEL_PROC,   curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(C.CONFIRM_YES, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(C.CONFIRM_NO, curses.COLOR_WHITE, curses.COLOR_BLACK)


def usage_color(pct):
    if pct >= 80:
        return curses.color_pair(C.CRIT) | curses.A_BOLD
    if pct >= 60:
        return curses.color_pair(C.WARN) | curses.A_BOLD
    return curses.color_pair(C.GOOD)
