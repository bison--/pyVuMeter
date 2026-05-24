import math
import random
import struct
import subprocess
import sys
import threading
import time

from .constants import (
    BYTES_PER_SAMPLE, CHANNELS, CHUNK_FRAMES,
    DB_MIN, DB_MAX, FPS_INTERVAL, SAMPLE_RATE,
)


def compute_rms(samples: list[int]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def rms_to_db(rms: float) -> float:
    if rms <= 0:
        return DB_MIN
    db = 20.0 * math.log10(rms / 32767.0)
    return max(DB_MIN, min(DB_MAX, db))


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
        cmd = ['arecord', '-f', 'S16_LE', '-r', str(SAMPLE_RATE), '-c', str(CHANNELS), '-q']
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
