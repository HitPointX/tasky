#!/usr/bin/env python3
"""Tasky — lightweight terminal system monitor for Apple Silicon Macs."""
import curses
import sys
from tasky.app import App


def main():
    if sys.platform != 'darwin':
        print('Tasky is designed for macOS (Apple Silicon).', file=sys.stderr)
        sys.exit(1)

    app = App()
    try:
        curses.wrapper(app.run)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
