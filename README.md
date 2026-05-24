# pyVuMeter

A VU meter for the CLI. Reads audio via ALSA `arecord` and displays a
real-time stereo level meter in the terminal.

[![Demo](https://img.youtube.com/vi/3rcy8Lg7rx4/maxresdefault.jpg)](https://www.youtube.com/watch?v=3rcy8Lg7rx4)

## Requirements

- Python 3.10+
- `arecord` from `alsa-utils`

## Usage

```bash
# via start script (recommended)
./run.py [OPTIONS]

# or as a module
python3 -m vu_meter [OPTIONS]
```

### Options

| Option | Description |
|---|---|
| `-D DEV`, `--device DEV` | ALSA capture device to record from (e.g. `hw:0,0`, `hw:1,0`). Defaults to the ALSA default device. |
| `--test` | Run with simulated audio - no sound card or `arecord` required. Useful for testing the display. |
| `-h`, `--help` | Show help and exit. |

### Examples

```bash
# Use the default ALSA capture device
./run.py

# Use a specific device (list devices with: arecord -l)
./run.py -D hw:1,0

# Test the display without audio hardware
./run.py --test
```

## Controls

| Key | Action |
|---|---|
| `q` / `Q` / `Esc` | Quit |

