#!/usr/bin/env python3
"""CLI VU Meter - reads audio via arecord (ALSA) and displays in terminal."""

import argparse
import curses
import math
import struct
import subprocess
import sys
import threading
import time

SAMPLE_RATE = 44100
CHANNELS = 2
BYTES_PER_SAMPLE = 2  # S16_LE
CHUNK_FRAMES = 1024

DB_MIN = -60.0
DB_MAX = 0.0

PEAK_HOLD_FRAMES = 40
PEAK_DECAY_DB = 0.8
FPS_INTERVAL = 0.033  # ~30 fps


def rms_to_db(rms: float) -> float:
    if rms <= 0:
        return DB_MIN
    db = 20.0 * math.log10(rms / 32767.0)
    return max(DB_MIN, min(DB_MAX, db))


def db_to_ratio(db: float) -> float:
    return (db - DB_MIN) / (DB_MAX - DB_MIN)


def compute_rms(samples: list[int]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class AudioSource:
    def __init__(self):
        self._levels = [DB_MIN] * CHANNELS
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def get_levels(self) -> list[float]:
        with self._lock:
            return list(self._levels)

    def _set_levels(self, levels: list[float]):
        with self._lock:
            self._levels = levels

    def _run(self):
        raise NotImplementedError

    def _parse_chunk(self, data: bytes) -> list[float]:
        n_frames = len(data) // (CHANNELS * BYTES_PER_SAMPLE)
        n_samples = n_frames * CHANNELS
        samples = struct.unpack(f'<{n_samples}h', data[: n_samples * BYTES_PER_SAMPLE])
        ch_samples: list[list[int]] = [[] for _ in range(CHANNELS)]
        for i, s in enumerate(samples):
            ch_samples[i % CHANNELS].append(s)
        return [rms_to_db(compute_rms(ch)) for ch in ch_samples]


class AlsaSource(AudioSource):
    def __init__(self, device: str | None):
        super().__init__()
        self._device = device

    def _run(self):
        cmd = [
            'arecord',
            '-f', 'S16_LE',
            '-r', str(SAMPLE_RATE),
            '-c', str(CHANNELS),
            '-q',
        ]
        if self._device:
            cmd += ['-D', self._device]
        cmd.append('-')

        chunk_bytes = CHUNK_FRAMES * CHANNELS * BYTES_PER_SAMPLE
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            sys.exit('Error: arecord not found. Install alsa-utils or use --test.')

        try:
            while self._running:
                data = proc.stdout.read(chunk_bytes)
                if not data:
                    break
                self._set_levels(self._parse_chunk(data))
        finally:
            proc.terminate()


class TestSource(AudioSource):
    """Simulated audio for testing without hardware."""

    def _run(self):
        t = 0.0
        import random
        while self._running:
            levels = []
            for ch in range(CHANNELS):
                freq = 0.4 + ch * 0.25
                envelope = (math.sin(2 * math.pi * freq * t) + 1) / 2
                noise = 0.85 + 0.15 * random.random()
                rms = envelope * noise * 32767 * 0.75
                levels.append(rms_to_db(rms))
            self._set_levels(levels)
            t += FPS_INTERVAL
            time.sleep(FPS_INTERVAL)


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


def color_for_ratio(ratio: float) -> int:
    if ratio < 0.70:
        return 1  # green
    elif ratio < 0.85:
        return 2  # yellow
    else:
        return 3  # red


def draw_bar(win, y: int, x: int, width: int, db: float, peak_db: float, label: str):
    filled = int(db_to_ratio(db) * width)
    peak_pos = int(db_to_ratio(peak_db) * width)
    peak_pos = min(peak_pos, width - 1)

    win.addstr(y, x, label, curses.A_BOLD)
    bx = x + len(label) + 1

    for i in range(width):
        ratio = i / width
        color = color_for_ratio(ratio)

        if i == peak_pos and peak_db > DB_MIN:
            win.addstr(y, bx + i, '▌', curses.color_pair(color) | curses.A_BOLD)
        elif i < filled:
            win.addstr(y, bx + i, '█', curses.color_pair(color))
        else:
            try:
                win.addstr(y, bx + i, '░', curses.color_pair(4))
            except curses.error:
                pass

    db_str = f'  {db:5.1f} dB'
    try:
        win.addstr(y, bx + width, db_str, curses.color_pair(5))
    except curses.error:
        pass


def draw_scale(win, y: int, bx: int, bar_width: int):
    marks = [(-60, '-60'), (-40, '-40'), (-20, '-20'), (-10, '-10'),
             (-6, '-6'), (-3, '-3'), (0, '0')]

    tick_row = [' '] * bar_width
    label_row = [' '] * bar_width

    for db, label in marks:
        pos = int(db_to_ratio(db) * bar_width)
        pos = min(pos, bar_width - 1)
        tick_row[pos] = '┬'
        start = max(0, pos - len(label) // 2)
        for j, ch in enumerate(label):
            idx = start + j
            if idx < bar_width:
                label_row[idx] = ch

    try:
        win.addstr(y, bx, ''.join(tick_row), curses.color_pair(6))
        win.addstr(y + 1, bx, ''.join(label_row), curses.color_pair(6))
    except curses.error:
        pass


def run_ui(stdscr, source: AudioSource, args: argparse.Namespace):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    stdscr.nodelay(True)

    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, 8 if curses.COLORS >= 16 else curses.COLOR_BLACK, -1)
    curses.init_pair(5, curses.COLOR_WHITE, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_BLUE, -1)

    peaks = PeakTracker(CHANNELS)
    ch_names = ['L', 'R'] if CHANNELS == 2 else [str(i) for i in range(CHANNELS)]
    mode_label = '[TEST]' if args.test else f'[{args.device or "default"}]'

    while True:
        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27):
            break

        height, width = stdscr.getmaxyx()
        stdscr.erase()

        # fixed widths
        label_w = 2        # 'L ' or 'R '
        db_w = 10          # '  -60.0 dB'
        padding = 4
        bar_w = max(10, width - label_w - db_w - padding)
        bar_x = padding // 2 + label_w + 1  # where bars start

        # Title
        title = '[ VU METER ]'
        title_full = f'{title}  {mode_label}'
        try:
            stdscr.addstr(0, max(0, (width - len(title_full)) // 2), title_full,
                          curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(1, 0, '─' * (width - 1), curses.color_pair(7))
        except curses.error:
            pass

        # Bars
        levels = source.get_levels()
        peak_levels = peaks.update(levels)

        for i, (db, name) in enumerate(zip(levels, ch_names)):
            row = 3 + i * 3
            if row >= height - 4:
                break
            draw_bar(stdscr, row, padding // 2, bar_w, db, peak_levels[i], name)

        # Scale
        scale_y = 3 + CHANNELS * 3
        if scale_y + 2 < height:
            try:
                stdscr.addstr(scale_y, padding // 2, '─' * (label_w + 1 + bar_w),
                              curses.color_pair(7))
            except curses.error:
                pass
            draw_scale(stdscr, scale_y + 1, padding // 2 + label_w + 1, bar_w)

        # Footer
        try:
            stdscr.addstr(height - 1, 0, ' q: quit', curses.color_pair(6))
        except curses.error:
            pass

        stdscr.refresh()
        time.sleep(FPS_INTERVAL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='CLI VU Meter via ALSA arecord')
    parser.add_argument('-D', '--device', metavar='DEV',
                        help='ALSA capture device (e.g. hw:0,0)')
    parser.add_argument('--test', action='store_true',
                        help='Run with simulated audio (no ALSA required)')
    return parser.parse_args()


def main():
    args = parse_args()
    source: AudioSource = TestSource() if args.test else AlsaSource(args.device)
    source.start()
    try:
        curses.wrapper(run_ui, source, args)
    finally:
        source.stop()


if __name__ == '__main__':
    main()
