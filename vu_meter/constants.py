SAMPLE_RATE = 44100
CHANNELS = 2
BYTES_PER_SAMPLE = 2  # S16_LE
CHUNK_FRAMES = 1024

DB_MIN = -60.0
DB_MAX = 0.0

PEAK_HOLD_FRAMES = 40
PEAK_DECAY_DB = 0.8
FPS_INTERVAL = 0.033  # ~30 fps

SCALE_MARKS = [
    (-60, '-60'), (-40, '-40'), (-20, '-20'), (-10, '-10'),
    (-6, '-6'), (-3, '-3'), (0, '0'),
]

CH_NAMES = ['L', 'R'] if CHANNELS == 2 else [str(i) for i in range(CHANNELS)]
