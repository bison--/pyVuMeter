import curses
import time

from .audio import AudioSource
from .constants import FPS_INTERVAL
from .display import Renderer


class VUMeter:
    def __init__(self, source: AudioSource, mode_label: str):
        self._source = source
        self._mode_label = mode_label

    def run(self):
        self._source.start()
        try:
            curses.wrapper(self._ui_loop)
        finally:
            self._source.stop()

    def _ui_loop(self, stdscr):
        renderer = Renderer(stdscr, self._mode_label)
        while True:
            key = stdscr.getch()
            if key in (ord('q'), ord('Q'), 27):
                break
            renderer.draw(self._source.get_levels())
            time.sleep(FPS_INTERVAL)
