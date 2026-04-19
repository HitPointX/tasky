import curses
import time
import socket
import os
from . import colors as col
from .colors import C
from . import graphs as g


def _fmt_uptime(seconds):
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s   = divmod(rem, 60)
    if d:
        return f'{d}d {h}h {m}m'
    if h:
        return f'{h}h {m}m {s}s'
    return f'{m}m {s}s'


def _fmt_cmd(proc):
    """Format process cmdline the Glances way: exe basename + args."""
    cmd = proc.get('cmdline') or []
    if not cmd:
        return f'[{proc.get("name") or "?"}]'
    exe = os.path.basename(cmd[0]) if cmd[0] else (proc.get('name') or '?')
    args = ' '.join(cmd[1:]) if len(cmd) > 1 else ''
    return f'{exe} {args}' if args else exe


# ── helpers ──────────────────────────────────────────────────────────────────

def _w(screen, y, x, text, attr=0):
    """Safe addstr: clips to screen bounds."""
    h, w = screen.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    if x + len(text) > w:
        text = text[:max(0, w - x)]
    if not text:
        return
    try:
        screen.addstr(y, x, text, attr)
    except curses.error:
        pass


def _hline(screen, y, x, char, n, attr=0):
    h, w = screen.getmaxyx()
    if y < 0 or y >= h:
        return
    n = min(n, w - x)
    if n <= 0:
        return
    try:
        # hline only handles ASCII/ACS chars; use addstr for Unicode line-drawing
        screen.addstr(y, x, char * n, attr)
    except curses.error:
        pass


def _fill_line(screen, y, attr=0):
    _, w = screen.getmaxyx()
    _w(screen, y, 0, ' ' * w, attr)


# ── structural chrome ─────────────────────────────────────────────────────────

TABS = ['CPU', 'NETWORK', 'GPU', 'FANS']
TAB_KEYS = ['1', '2', '3', '4']


def draw_header(screen, w):
    attr = curses.color_pair(C.HEADER) | curses.A_BOLD
    _fill_line(screen, 0, attr)
    title = '  TASKY'
    _w(screen, 0, 0, title, attr)
    ts = time.strftime('%H:%M:%S')
    try:
        host = socket.gethostname().split('.')[0]
    except Exception:
        host = 'localhost'
    right = f'{host}  {ts}  '
    _w(screen, 0, w - len(right), right, attr)


def draw_tabs(screen, w, current):
    y = 1
    _fill_line(screen, y, curses.color_pair(C.BORDER))
    x = 2
    for i, tab in enumerate(TABS):
        label = f' {TAB_KEYS[i]}:{tab} '
        if i == current:
            attr = curses.color_pair(C.TAB_SEL) | curses.A_BOLD
        else:
            attr = curses.color_pair(C.TAB_UNSEL)
        _w(screen, y, x, label, attr)
        x += len(label) + 1

    help_r = '  ←→/Tab: switch  q: quit  '
    _w(screen, y, w - len(help_r), help_r, curses.color_pair(C.BORDER))


def draw_border_row(screen, y, w):
    _hline(screen, y, 0, '─', w, curses.color_pair(C.BORDER))


def draw_footer(screen, h, w):
    y = h - 1
    attr = curses.color_pair(C.BORDER)
    _fill_line(screen, y, attr)
    _w(screen, y, 1, ' ← → Tab: switch tabs   1-4: jump   q / ESC: quit ', attr)


# ── CPU view ─────────────────────────────────────────────────────────────────

def draw_cpu(screen, h, w, collector, sel_pid=None, scroll=0):
    d = collector.get_data()
    if not d:
        _w(screen, 4, 2, 'Collecting…', curses.color_pair(C.DIM))
        return

    row = 2
    brand = d.get('brand', '')
    p = d.get('cpu_count_phys', 1)
    l = d.get('cpu_count_logic', 1)
    uptime_s = _fmt_uptime(d.get('uptime_s', 0))
    _w(screen, row, 2, f'{brand}   {p}P / {l}L cores', curses.color_pair(C.WHITE) | curses.A_BOLD)
    _w(screen, row, w - len(uptime_s) - 3, f'up {uptime_s}', curses.color_pair(C.DIM))
    row += 1

    # Overall CPU bar + sparkline
    cpu_pct = d.get('cpu_pct', 0.0)
    bar_w = min(40, w - 30)
    bar_str = g.bar(cpu_pct, 100, bar_w)
    spark = g.sparkline(d.get('cpu_history', []), width=20)
    cpu_attr = col.usage_color(cpu_pct)
    _w(screen, row, 2, 'CPU  ', curses.color_pair(C.BORDER) | curses.A_BOLD)
    _w(screen, row, 7, bar_str, cpu_attr)
    _w(screen, row, 7 + bar_w + 1, f'{cpu_pct:5.1f}%  [{spark}]', cpu_attr)
    row += 1

    # Memory bar
    mem_pct = d.get('mem_pct', 0.0)
    mem_used = d.get('mem_used', 0)
    mem_total = d.get('mem_total', 0)
    mem_bar = g.bar(mem_pct, 100, bar_w)
    mem_attr = col.usage_color(mem_pct)
    _w(screen, row, 2, 'MEM  ', curses.color_pair(C.BORDER) | curses.A_BOLD)
    _w(screen, row, 7, mem_bar, mem_attr)
    used_s = g.fmt_bytes(mem_used)
    total_s = g.fmt_bytes(mem_total)
    _w(screen, row, 7 + bar_w + 1, f'{mem_pct:5.1f}%  {used_s} / {total_s}', mem_attr)
    row += 1

    # Load averages + freq
    load = d.get('load', (0, 0, 0))
    freq = d.get('freq_mhz', 0)
    freq_s = f'{freq/1000:.2f} GHz' if freq > 0 else 'N/A'
    _w(screen, row, 2,
       f'Load  {load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}  (1m 5m 15m)    Freq {freq_s}',
       curses.color_pair(C.DIM) | curses.A_BOLD)
    row += 1

    # Per-core bars
    core_pcts = d.get('core_pcts', [])
    if core_pcts:
        _w(screen, row, 2, 'Cores:', curses.color_pair(C.BORDER))
        row += 1
        core_bar_w = 10
        cols = max(1, (w - 4) // (core_bar_w + 10))
        for i, cpct in enumerate(core_pcts):
            col_idx = i % cols
            row_off = i // cols
            x = 2 + col_idx * ((core_bar_w + 10))
            y = row + row_off
            if y >= h - 2:
                break
            cbar = g.bar(cpct, 100, core_bar_w)
            cattr = col.usage_color(cpct)
            _w(screen, y, x, f'C{i:<2} ', curses.color_pair(C.DIM))
            _w(screen, y, x + 4, cbar, cattr)
            _w(screen, y, x + 4 + core_bar_w, f' {cpct:4.1f}%', cattr)
        row += (len(core_pcts) - 1) // cols + 2

    # Process table
    if row >= h - 2:
        return

    # Fixed columns: PID(7) + CPU%(6) + MEM%(5) + STATUS(8) + spacing(10) = 36
    # Remaining width goes to COMMAND
    cmd_w = max(20, w - 38)
    hdr_attr = curses.color_pair(C.BORDER) | curses.A_BOLD
    hint = '  ↑↓ select  K kill  ESC clear' if sel_pid is None else '  K kill  ESC clear'
    hdr = f"{'PID':>7}  {'COMMAND':<{cmd_w}}  {'CPU%':>6}  {'MEM%':>5}  STATUS"
    _w(screen, row, 2, hdr[:w - 3], hdr_attr)
    _w(screen, row, w - len(hint) - 1, hint[:w // 3], curses.color_pair(C.DIM))
    row += 1

    all_procs = d.get('processes', [])
    visible = all_procs[scroll:]
    for proc in visible:
        if row >= h - 1:
            break
        pid    = proc.get('pid') or 0
        cpu    = float(proc.get('cpu_percent') or 0.0)
        mem    = float(proc.get('memory_percent') or 0.0)
        status = (proc.get('status') or '')[:8]
        cmd    = _fmt_cmd(proc)[:cmd_w]

        is_sel = (pid == sel_pid)
        if is_sel:
            p_attr = curses.color_pair(C.SEL_PROC) | curses.A_BOLD
        elif cpu >= 10:
            p_attr = col.usage_color(cpu)
        else:
            p_attr = curses.color_pair(C.WHITE)

        line = f'{pid:>7}  {cmd:<{cmd_w}}  {cpu:>6.1f}  {mem:>5.1f}  {status}'
        text = line[:w - 3]
        if is_sel:
            # Pad to full width so background fills the row
            text = text.ljust(w - 3)
        _w(screen, row, 2, text, p_attr)
        row += 1


# ── Network view ──────────────────────────────────────────────────────────────

def draw_network(screen, h, w, collector):
    d = collector.get_data()
    if not d:
        _w(screen, 4, 2, 'Collecting…', curses.color_pair(C.DIM))
        return

    interfaces = d.get('interfaces', [])
    row = 2
    graph_h = 8

    for iface in interfaces:
        if row >= h - 1:
            break

        name = iface['name']
        ipv4 = iface.get('ipv4', '') or '—'
        rx = iface['rx_rate']
        tx = iface['tx_rate']
        is_up = iface.get('is_up', False)

        up_attr = curses.color_pair(C.GOOD) if is_up else curses.color_pair(C.CRIT)
        up_s = 'UP' if is_up else 'DN'
        _w(screen, row, 2, f'● {name:<8}', up_attr | curses.A_BOLD)
        _w(screen, row, 13, f'{ipv4:<16}', curses.color_pair(C.WHITE))
        _w(screen, row, 30, f'↓ {g.fmt_bytes_rate(rx):<14}', curses.color_pair(C.BLUE) | curses.A_BOLD)
        _w(screen, row, 46, f'↑ {g.fmt_bytes_rate(tx):<14}', curses.color_pair(C.MAGENTA) | curses.A_BOLD)
        _w(screen, row, 62, f'[{up_s}]', up_attr)
        row += 1

        # Area graph for this interface
        graph_w = min(w - 10, 70)
        if row + graph_h + 3 < h and graph_w > 10:
            rx_hist = iface.get('rx_history', [])
            tx_hist = iface.get('tx_history', [])
            combined = [max(a, b) for a, b in zip(rx_hist, tx_hist)]
            max_v = max(combined) if combined and max(combined) > 0 else 1.0

            rx_rows, _ = g.area_graph(rx_hist, graph_h, graph_w, max_value=max_v)
            tx_rows, _ = g.area_graph(tx_hist, graph_h, graph_w, max_value=max_v)

            # Y-axis label width
            y_label = g.fmt_bytes_rate(max_v)
            _w(screen, row, 4, f'↓ RX  max {y_label}', curses.color_pair(C.BLUE))
            row += 1
            for r_row in rx_rows:
                _w(screen, row, 4, '│', curses.color_pair(C.BORDER))
                _w(screen, row, 5, r_row, curses.color_pair(C.BLUE))
                _w(screen, row, 5 + graph_w, '│', curses.color_pair(C.BORDER))
                row += 1
            _hline(screen, row, 4, '─', graph_w + 2, curses.color_pair(C.BORDER))
            row += 1

            _w(screen, row, 4, f'↑ TX  max {y_label}', curses.color_pair(C.MAGENTA))
            row += 1
            for t_row in tx_rows:
                _w(screen, row, 4, '│', curses.color_pair(C.BORDER))
                _w(screen, row, 5, t_row, curses.color_pair(C.MAGENTA))
                _w(screen, row, 5 + graph_w, '│', curses.color_pair(C.BORDER))
                row += 1
            _hline(screen, row, 4, '─', graph_w + 2, curses.color_pair(C.BORDER))
            row += 2

        else:
            # Compact sparkline
            spark_w = min(40, w - 30)
            rx_spark = g.sparkline(iface.get('rx_history', []), width=spark_w)
            tx_spark = g.sparkline(iface.get('tx_history', []), width=spark_w)
            _w(screen, row, 4, f'↓ [{rx_spark}]', curses.color_pair(C.BLUE))
            row += 1
            _w(screen, row, 4, f'↑ [{tx_spark}]', curses.color_pair(C.MAGENTA))
            row += 2


# ── GPU view ──────────────────────────────────────────────────────────────────

def draw_gpu(screen, h, w, collector):
    d = collector.get_data()
    if not d:
        _w(screen, 4, 2, 'Collecting…', curses.color_pair(C.DIM))
        return

    row = 2
    name = d.get('name', 'Unknown GPU')
    _w(screen, row, 2, name, curses.color_pair(C.WHITE) | curses.A_BOLD)
    row += 1

    if not d.get('available'):
        _w(screen, row, 2,
           'GPU data unavailable — ioreg returned no IOAccelerator entries.',
           curses.color_pair(C.WARN))
        return

    util = d.get('utilization', 0)
    rend = d.get('renderer_util', 0)
    tile = d.get('tiler_util', 0)
    bar_w = min(40, w - 30)

    # Device utilization
    _w(screen, row, 2, 'GPU    ', curses.color_pair(C.BORDER) | curses.A_BOLD)
    _w(screen, row, 9, g.bar(util, 100, bar_w), col.usage_color(util))
    _w(screen, row, 9 + bar_w + 1, f'{util:5.1f}%', col.usage_color(util))
    row += 1

    _w(screen, row, 2, 'Render ', curses.color_pair(C.BORDER) | curses.A_BOLD)
    _w(screen, row, 9, g.bar(rend, 100, bar_w), col.usage_color(rend))
    _w(screen, row, 9 + bar_w + 1, f'{rend:5.1f}%', col.usage_color(rend))
    row += 1

    _w(screen, row, 2, 'Tiler  ', curses.color_pair(C.BORDER) | curses.A_BOLD)
    _w(screen, row, 9, g.bar(tile, 100, bar_w), col.usage_color(tile))
    _w(screen, row, 9 + bar_w + 1, f'{tile:5.1f}%', col.usage_color(tile))
    row += 1

    # VRAM
    vram_total = d.get('vram_total_mb', 0)
    vram_used = d.get('vram_used_mb', 0)
    if vram_total > 0:
        vram_pct = vram_used / vram_total * 100
        _w(screen, row, 2, 'VRAM   ', curses.color_pair(C.BORDER) | curses.A_BOLD)
        _w(screen, row, 9, g.bar(vram_pct, 100, bar_w), col.usage_color(vram_pct))
        _w(screen, row, 9 + bar_w + 1,
           f'{vram_pct:5.1f}%  {vram_used} MB / {vram_total} MB',
           col.usage_color(vram_pct))
        row += 1
    else:
        _w(screen, row, 2,
           'VRAM   Unified memory (shared with system RAM)',
           curses.color_pair(C.DIM))
        row += 1

    row += 1

    # Utilization history graph
    graph_h = min(10, h - row - 3)
    graph_w = min(w - 10, 70)
    if graph_h >= 4 and graph_w > 10:
        _w(screen, row, 2, 'GPU Utilization (60s)', curses.color_pair(C.BORDER))
        row += 1
        hist = d.get('util_history', [])
        rows, max_v = g.area_graph(hist, graph_h, graph_w, max_value=100)
        _w(screen, row, 2, f'100%│', curses.color_pair(C.DIM))
        for i, gr in enumerate(rows):
            _w(screen, row + i, 6, gr, col.usage_color(util))
        _w(screen, row, 6 + graph_w, '│', curses.color_pair(C.BORDER))
        _hline(screen, row + graph_h, 6, '─', graph_w, curses.color_pair(C.BORDER))
        _w(screen, row + graph_h, 2, '  0%└', curses.color_pair(C.DIM))


# ── Fan view ──────────────────────────────────────────────────────────────────

def draw_fans(screen, h, w, collector):
    d = collector.get_data()
    if not d:
        _w(screen, 4, 2, 'Collecting…', curses.color_pair(C.DIM))
        return

    row = 2
    fans = d.get('fans', [])

    if not fans:
        needs_sudo = d.get('needs_sudo', False)
        if needs_sudo:
            _w(screen, row, 2, '● Fan data unavailable', curses.color_pair(C.WARN) | curses.A_BOLD)
            row += 1
            _w(screen, row, 4, 'Restart Tasky and choose y at the fan monitoring prompt.',
               curses.color_pair(C.DIM))
            row += 1
            _w(screen, row, 4, 'A sudo password is required once per session.',
               curses.color_pair(C.DIM))
        else:
            _w(screen, row, 2, '● No fans detected', curses.color_pair(C.GOOD) | curses.A_BOLD)
            row += 1
            _w(screen, row, 4, 'This Mac appears to be fanless (passive cooling only).',
               curses.color_pair(C.DIM))
        return

    bar_w = min(40, w - 40)

    for fan in fans:
        if row >= h - 1:
            break
        label = fan.get('label', f'Fan {fan["id"]}')
        rpm = fan.get('rpm', 0.0)
        max_rpm = fan.get('max_rpm', 6000.0) or 6000.0
        min_rpm = fan.get('min_rpm', 0.0)
        pct = (rpm - min_rpm) / (max_rpm - min_rpm) * 100 if max_rpm > min_rpm else 0

        stopped = rpm == 0.0
        fan_attr = curses.color_pair(C.DIM) if stopped else col.usage_color(pct)
        rpm_s = 'idle' if stopped else f'{rpm:.0f} RPM  ({pct:.0f}%)'
        _w(screen, row, 2, f'{label:<10}', curses.color_pair(C.BORDER) | curses.A_BOLD)
        _w(screen, row, 13, g.bar(pct, 100, bar_w), fan_attr)
        _w(screen, row, 13 + bar_w + 1, f'  {rpm_s}', fan_attr)
        row += 1

        # Sparkline history
        history = fan.get('history', [])
        if history:
            spark = g.sparkline(history, width=min(50, w - 20))
            _w(screen, row, 4, f'[{spark}]', curses.color_pair(C.DIM))
            row += 1

        row += 1

    # Graph for first fan
    if fans and row < h - 6:
        fan = fans[0]
        history = fan.get('history', [])
        graph_h = min(8, h - row - 3)
        graph_w = min(w - 10, 70)
        if history and graph_h >= 4 and graph_w > 10:
            max_rpm = fan.get('max_rpm', 6000.0) or 6000.0
            _w(screen, row, 2,
               f'{fan.get("label", "Fan 0")} History (60s)',
               curses.color_pair(C.BORDER))
            row += 1
            rows, _ = g.area_graph(history, graph_h, graph_w, max_value=max_rpm)
            _w(screen, row, 2, f'{max_rpm:.0f}│', curses.color_pair(C.DIM))
            for i, gr in enumerate(rows):
                _w(screen, row + i, 7, gr, curses.color_pair(C.GOOD))
            _w(screen, row, 7 + graph_w, '│', curses.color_pair(C.BORDER))
            _hline(screen, row + graph_h, 7, '─', graph_w, curses.color_pair(C.BORDER))
            _w(screen, row + graph_h, 2, '     0└', curses.color_pair(C.DIM))


# ── Kill confirmation overlay ─────────────────────────────────────────────────

def draw_kill_confirm(screen, h, w, pid, name, yes):
    box_w = 44
    box_h = 5
    y0 = h // 2 - box_h // 2
    x0 = w // 2 - box_w // 2

    # Shadow + border
    border_attr = curses.color_pair(C.CRIT) | curses.A_BOLD
    blank = ' ' * box_w
    for row in range(box_h):
        _w(screen, y0 + row, x0, blank, curses.color_pair(C.WHITE))

    _w(screen, y0,           x0, '┌' + '─' * (box_w - 2) + '┐', border_attr)
    _w(screen, y0 + box_h-1, x0, '└' + '─' * (box_w - 2) + '┘', border_attr)
    for r in range(1, box_h - 1):
        _w(screen, y0 + r, x0,           '│', border_attr)
        _w(screen, y0 + r, x0 + box_w-1, '│', border_attr)

    # Title
    title = f' Kill {name} (PID {pid})? '
    title = title[:box_w - 4]
    tx = x0 + (box_w - len(title)) // 2
    _w(screen, y0 + 1, tx, title, curses.color_pair(C.CRIT) | curses.A_BOLD)

    # YES / NO buttons
    yes_attr = curses.color_pair(C.CONFIRM_YES) | curses.A_BOLD
    no_attr  = curses.color_pair(C.CONFIRM_NO)  | curses.A_BOLD

    yes_label = '  YES  '
    no_label  = '  NO   '
    btn_y = y0 + 3
    btn_x = x0 + box_w // 2 - 9

    _w(screen, btn_y, btn_x,              yes_label, yes_attr if yes  else curses.color_pair(C.WHITE))
    _w(screen, btn_y, btn_x + 9,          no_label,  no_attr  if not yes else curses.color_pair(C.WHITE))

    hint = ' ← → choose   Enter confirm   ESC cancel '
    _w(screen, y0 + box_h, x0, hint[:box_w], curses.color_pair(C.DIM))
