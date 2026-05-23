# pyVuMeter

A VU meter for the CLI. Reads audio via ALSA `arecord` and displays a
real-time stereo level meter in the terminal.

## Requirements

- Python 3.10+
- `arecord` from `alsa-utils` (pre-installed on the target system)

## Usage

```
python3 vu_meter.py [OPTIONS]
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
python3 vu_meter.py

# Use a specific device (list devices with: arecord -l)
python3 vu_meter.py -D hw:1,0

# Test the display without audio hardware
python3 vu_meter.py --test
```

## Controls

| Key | Action |
|---|---|
| `q` / `Q` / `Esc` | Quit |

