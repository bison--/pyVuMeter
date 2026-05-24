import argparse

from .audio import AlsaSource, AudioSource, TestSource
from .meter import VUMeter


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
    mode_label = '[TEST]' if args.test else f'[{args.device or "default"}]'
    VUMeter(source, mode_label).run()


if __name__ == '__main__':
    main()
