import curses
import sys
from .app import App


def main():
    if sys.platform != 'darwin':
        print('Tasky is designed for macOS (Apple Silicon / Intel).', file=sys.stderr)
        sys.exit(1)

    app = App()
    try:
        curses.wrapper(app.run)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
