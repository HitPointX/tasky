SPARKS = ' ▁▂▃▄▅▆▇█'
FILL_BLOCKS = ' ▁▂▃▄▅▆▇█'
BAR_FULL = '█'
BAR_EMPTY = '░'


def sparkline(values, width=None):
    if not values:
        return ''
    data = _sample(list(values), width) if width else list(values)
    if not data:
        return ''
    max_v = max(data) or 1
    return ''.join(SPARKS[min(int(v / max_v * (len(SPARKS) - 1)), len(SPARKS) - 1)] for v in data)


def bar(value, max_value, width, fill=BAR_FULL, empty=BAR_EMPTY):
    if max_value <= 0:
        filled = 0
    else:
        filled = int(value / max_value * width)
    filled = max(0, min(filled, width))
    return fill * filled + empty * (width - filled)


def area_graph(history, height, width, max_value=None, scale_label=True):
    """Return (rows, y_max) where rows is a list of strings, top→bottom."""
    data = _sample(list(history), width)
    if max_value is None:
        max_value = max(data) if data and max(data) > 0 else 1.0

    rows = []
    for row_idx in range(height - 1, -1, -1):
        row_min = row_idx / height * max_value
        row_max = (row_idx + 1) / height * max_value
        line = []
        for val in data:
            if val >= row_max:
                line.append('█')
            elif val <= row_min:
                line.append(' ')
            else:
                frac = (val - row_min) / (row_max - row_min) if row_max > row_min else 0
                idx = max(1, min(int(frac * 8), 8))
                line.append(FILL_BLOCKS[idx])
        rows.append(''.join(line))

    return rows, max_value


def fmt_bytes(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024.0:
            return f'{n:.1f} {unit}'
        n /= 1024.0
    return f'{n:.1f} PB'


def fmt_bytes_rate(n):
    return fmt_bytes(n) + '/s'


def _sample(values, target):
    if not values or target is None:
        return values or []
    n = len(values)
    if n == target:
        return values
    if n < target:
        return [0.0] * (target - n) + values
    step = n / target
    return [values[int(i * step)] for i in range(target)]
