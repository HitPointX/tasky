# Tasky

Lightweight terminal system monitor for macOS. Real-time views for CPU (per-core usage, process list with full command paths), memory, network traffic with ASCII graphs, GPU utilization, and fan speeds. Color-coded, tab-based interface with process management. Supports Apple Silicon and Intel Macs.

---

## Features

- **Four live views** — CPU, Network, GPU, and Fans, each with scrolling history graphs
- **Color-coded utilization** — green → yellow → red thresholds across all metrics
- **ASCII area graphs** — scrolling filled graphs built from Unicode block characters (`▁▂▃▄▅▆▇█`)
- **Process management** — navigate the process list, inspect full command paths, and send SIGTERM with a confirmation dialog
- **Apple Silicon GPU** — utilization, renderer and tiler breakdown via IOKit (no `sudo` required)
- **Fan speeds** — direct SMC read via IOKit, no third-party tools or `sudo` needed; gracefully shows `idle` when fans are stopped at low load
- **Uptime display** — system uptime shown alongside the CPU brand in the header
- **Lightweight** — single dependency (`psutil`), all rendering through the standard `curses` library

---

## Requirements

- macOS (Apple Silicon M1–M5 or Intel)
- Python 3.9+
- No Homebrew packages or system-level installs required

---

## Dependencies

### Python package (the only `pip install`)

| Package | Version | Purpose |
|---------|---------|---------|
| [`psutil`](https://github.com/giampaolo/psutil) | ≥ 5.9.0 | CPU %, per-core stats, memory, network I/O, process list |

Everything else is either Python stdlib or a macOS system component:

### Python stdlib (no install needed)

`curses` · `ctypes` · `collections` · `json` · `os` · `platform` · `re` · `signal` · `socket` · `struct` · `subprocess` · `sys` · `threading` · `time`

### macOS system frameworks (always present, accessed via `ctypes`)

| Framework | Path | Used for |
|-----------|------|---------|
| IOKit | `/System/Library/Frameworks/IOKit.framework/IOKit` | SMC fan reads, GPU stats |
| libSystem | `/usr/lib/libSystem.B.dylib` | `mach_task_self_` port for SMC session |

### macOS CLI tools (bundled with macOS / Xcode Command Line Tools)

| Tool | Used for |
|------|---------|
| `ioreg` | GPU utilization and VRAM via IOAccelerator |
| `sysctl` | CPU brand string |
| `system_profiler` | GPU model name |

Xcode Command Line Tools can be installed with:
```bash
xcode-select --install
```

---

## Installation

### Homebrew (recommended)

```bash
brew tap HitPointX/tasky
brew install tasky
```

Then run from anywhere:

```bash
tasky
```

### From source

```bash
git clone https://github.com/HitPointX/tasky.git
cd tasky
python3 -m venv .venv
.venv/bin/pip install psutil
```

---

## Running (from source)

```bash
./tasky.sh
```

The launcher script creates and activates the virtual environment automatically on first run, then starts Tasky.

Alternatively, with the venv active:

```bash
.venv/bin/python3 main.py
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` / `→` | Next tab |
| `←` | Previous tab |
| `1` `2` `3` `4` | Jump to CPU / Network / GPU / Fans |
| `↑` `↓` | Navigate process list (CPU tab) |
| `K` | Kill selected process |
| `ESC` | Clear process selection / cancel dialog |
| `q` | Quit |

---

## Views

### 1 · CPU

```
Apple M5 Max   12P / 4L cores                              up 22h 13m 19s
CPU  ████████████████████░░░░░░░░░░░░░░░░░░░░  42.1%  [▁▂▃▄▅▆▇█▇▆]
MEM  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  38.4%  14.2 GB / 36.0 GB
Load  1.24  2.01  1.87  (1m 5m 15m)    Freq 4.05 GHz

Cores:
C0  ██████████ 100%   C1  ████░░░░░░  40%   C2  ██░░░░░░░░  20% ...

  PID    COMMAND                                CPU%   MEM%  STATUS
  926    Google Chrome --type=renderer          17.5    0.3   running
 3868    java -jar RuneLite.jar                 16.1    1.2   running
```

- Overall CPU and memory bars with inline sparkline history
- Per-core utilization bars, dynamically sized to terminal width
- Load averages (1m / 5m / 15m) and current CPU frequency
- Process list showing full command line and arguments
- Kernel threads shown as `[process_name]`
- Process list refreshes every 2 seconds; CPU and memory stats every 1 second

#### Process Selection & Kill

Press `↑` or `↓` on the CPU tab to activate the process selector.

- First `↑` → highlights the **top** process
- First `↓` → highlights the **bottom** process
- Subsequent presses scroll through the list
- Selection is highlighted in **baby blue**
- Selection auto-clears after **60 seconds** of inactivity

Press `K` on a highlighted process to open the kill confirmation dialog:

```
┌──────────────────────────────────────────┐
│       Kill Google Chrome (PID 926)?      │
│                                          │
│          YES              NO             │
└──────────────────────────────────────────┘
  ← → choose   Enter confirm   ESC cancel
```

Use `←` / `→` to toggle, `Enter` to confirm (sends `SIGTERM`), `ESC` to cancel.

---

### 2 · Network

```
● en0       192.168.1.100     ↓ 2.34 MB/s       ↑ 0.89 MB/s      [UP]

↓ RX  max 2.34 MB/s
│████████████████▆▄▂▁  ▁▂▄████████████▆▄│
────────────────────────────────────────
↑ TX  max 0.89 MB/s
│▁▁▁▁▂▃▄▅▄▃▂▁▁▁▂▃▄▅▆▅▄▃▂▁▂▁▁▁▁▁▁▁▁▁▁▁▁│
────────────────────────────────────────
```

- All active interfaces listed with IPv4 address and UP/DOWN status
- Separate scrolling area graphs for receive (blue) and transmit (magenta)
- Rates computed from delta between polls
- Falls back to compact sparkline view on small terminals

---

### 3 · GPU

```
Apple M5 Max

GPU    ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░  14.0%
Render ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   8.0%
Tiler  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   5.0%
VRAM   Unified memory (shared with system RAM)

GPU Utilization (60s)
100%│                              ▁▂▄▆██▆▄▂
    │
  0%└───────────────────────────────────────
```

- Overall device utilization, renderer, and tiler breakdown
- VRAM usage on discrete GPUs; unified memory note on Apple Silicon
- 60-second scrolling utilization history graph
- Data sourced via `ioreg` IOAccelerator — no `sudo` required
- Polls every 3 seconds to minimize subprocess overhead

---

### 4 · Fans

```
Fan 0      ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░   2840 RPM  (52%)
           [▁▁▁▁▁▂▂▃▃▄▄▅▅▆▆▇▇████▇▆▅▄▃▂▁▁▁▁▁]

Fan 1      ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░   2910 RPM  (50%)
           [▁▁▁▁▁▂▂▃▃▄▄▅▅▆▆▇▇████▇▆▅▄▃▂▁▁▁▁▁]
```

- Fan speeds read directly from the SMC via IOKit — **no `sudo` required**
- Shows RPM, percentage of max speed, and 60-second sparkline history
- Bar graph normalized between the fan's hardware-reported min and max RPM
- Shows `idle` when fans are fully stopped (common on Apple Silicon at low load)
- Tab is hidden automatically on fanless Macs (e.g. MacBook Air)

---

## Architecture

```
tasky/
├── main.py                 Entry point
├── tasky.sh                Self-contained launcher (handles venv)
├── requirements.txt        psutil only
└── tasky/
    ├── app.py              Main curses loop, key handling, selection state
    ├── config.py           Persistent settings (~/.config/tasky/settings.json)
    ├── collectors/
    │   ├── base.py         Threaded base collector with ring-buffer history
    │   ├── cpu.py          CPU %, per-core, load, process list (psutil)
    │   ├── network.py      Per-NIC rx/tx rates and history (psutil)
    │   ├── gpu.py          GPU utilization and VRAM via ioreg subprocess
    │   └── fans.py         Fan RPM via direct IOKit/SMC ctypes binding
    └── ui/
        ├── colors.py       Color palette and usage-level helpers
        ├── graphs.py       Sparkline, bar, and 2D area chart functions
        └── views.py        All tab renderers and overlay dialogs
```

Each collector runs in a **background thread**, updating a shared dict protected by a lock. The main loop renders at 1 Hz from cached data — collection and rendering are fully decoupled.

| Collector | Interval | Method |
|-----------|----------|--------|
| CPU stats | 1s | psutil (non-blocking) |
| Process list | 2s | psutil process_iter |
| Network | 1s | psutil net_io_counters |
| GPU | 3s | `ioreg` subprocess |
| Fans | 2s | IOKit SMC via ctypes |

---

## Notes

- **Apple Silicon fans** spin down completely at idle — `idle` is correct, not an error
- **GPU data** on Apple Silicon reflects the unified AGX accelerator; VRAM is shared system memory
- **Intel Macs** — CPU, memory, network, and process views work fully; GPU view depends on IOAccelerator availability; fan SMC keys follow the same `F0Ac` / `FNum` format
- Terminal must support **256 colors** for the baby blue process selection highlight; falls back to cyan on 16-color terminals
