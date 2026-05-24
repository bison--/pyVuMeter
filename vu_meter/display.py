import curses

from .constants import (
    CH_NAMES, CHANNELS, DB_MIN,
    PEAK_DECAY_DB, PEAK_HOLD_FRAMES, SCALE_MARKS,
)


def db_to_ratio(db: float) -> float:
    from .constants import DB_MIN, DB_MAX
    return (db - DB_MIN) / (DB_MAX - DB_MIN)


class PeakTracker:
    def __init__(self, channels: int):
        self._peaks = [DB_MIN] * channels
        self._hold = [0] * channels

    def update(self, levels: list[float]) -> list[float]:
        for i, db in enumerate(levels):
            if db >= self._peaks[i]:
                self._peaks[i] = db
                self._hold[i] = PEAK_HOLD_FRAMES
            elif self._hold[i] > 0:
                self._hold[i] -= 1
            else:
                self._peaks[i] = max(DB_MIN, self._peaks[i] - PEAK_DECAY_DB)
        return list(self._peaks)


class Renderer:
    PADDING = 2
    LABEL_W = 2   # 'L ' / 'R '
    DB_W = 10     # '  -60.0 dB'

    CP_GREEN = 1
    CP_YELLOW = 2
    CP_RED = 3
    CP_DIM = 4
    CP_WHITE = 5
    CP_CYAN = 6
    CP_BLUE = 7

    def __init__(self, stdscr, mode_label: str):
        self._win = stdscr
        self._mode_label = mode_label
        self._peaks = PeakTracker(CHANNELS)
        self._setup_colors()

    def _setup_colors(self):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        self._win.nodelay(True)

        curses.init_pair(self.CP_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(self.CP_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.CP_RED, curses.COLOR_RED, -1)
        curses.init_pair(self.CP_DIM, 8 if curses.COLORS >= 16 else curses.COLOR_BLACK, -1)
        curses.init_pair(self.CP_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(self.CP_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(self.CP_BLUE, curses.COLOR_BLUE, -1)

    def _color_for_ratio(self, ratio: float) -> int:
        if ratio < 0.70:
            return self.CP_GREEN
        elif ratio < 0.85:
            return self.CP_YELLOW
        else:
            return self.CP_RED

    def _draw_bar(self, y: int, x: int, bar_w: int, db: float, peak_db: float, label: str):
        self._win.addstr(y, x, label, curses.A_BOLD)
        bx = x + len(label) + 1
        filled = int(db_to_ratio(db) * bar_w)
        peak_pos = min(int(db_to_ratio(peak_db) * bar_w), bar_w - 1)

        for i in range(bar_w):
            color = curses.color_pair(self._color_for_ratio(i / bar_w))
            if i == peak_pos and peak_db > DB_MIN:
                self._win.addstr(y, bx + i, '▌', color | curses.A_BOLD)
            elif i < filled:
                self._win.addstr(y, bx + i, '█', color)
            else:
                try:
                    self._win.addstr(y, bx + i, '░', curses.color_pair(self.CP_DIM))
                except curses.error:
                    pass

        try:
            self._win.addstr(y, bx + bar_w, f'  {db:5.1f} dB',
                             curses.color_pair(self.CP_WHITE))
        except curses.error:
            pass

    def _draw_scale(self, y: int, bx: int, bar_w: int):
        tick_row = [' '] * bar_w
        label_row = [' '] * bar_w

        for db, label in SCALE_MARKS:
            pos = min(int(db_to_ratio(db) * bar_w), bar_w - 1)
            tick_row[pos] = '┬'
            start = max(0, pos - len(label) // 2)
            for j, ch in enumerate(label):
                idx = start + j
                if idx < bar_w:
                    label_row[idx] = ch

        try:
            self._win.addstr(y, bx, ''.join(tick_row), curses.color_pair(self.CP_CYAN))
            self._win.addstr(y + 1, bx, ''.join(label_row), curses.color_pair(self.CP_CYAN))
        except curses.error:
            pass

    def draw(self, levels: list[float]):
        peak_levels = self._peaks.update(levels)
        height, width = self._win.getmaxyx()
        self._win.erase()

        bar_w = max(10, width - self.LABEL_W - self.DB_W - self.PADDING * 2)
        x = self.PADDING

        title = f'[ VU METER ]  {self._mode_label}'
        try:
            self._win.addstr(0, max(0, (width - len(title)) // 2), title,
                             curses.color_pair(self.CP_WHITE) | curses.A_BOLD)
            self._win.addstr(1, 0, '─' * (width - 1), curses.color_pair(self.CP_BLUE))
        except curses.error:
            pass

        for i, (db, name) in enumerate(zip(levels, CH_NAMES)):
            row = 3 + i * 3
            if row >= height - 4:
                break
            self._draw_bar(row, x, bar_w, db, peak_levels[i], name)

        scale_y = 3 + CHANNELS * 3
        if scale_y + 2 < height:
            try:
                self._win.addstr(scale_y, x, '─' * (self.LABEL_W + 1 + bar_w),
                                 curses.color_pair(self.CP_BLUE))
            except curses.error:
                pass
            self._draw_scale(scale_y + 1, x + self.LABEL_W + 1, bar_w)

        try:
            self._win.addstr(height - 1, 0, ' q: quit', curses.color_pair(self.CP_CYAN))
        except curses.error:
            pass

        self._win.refresh()
