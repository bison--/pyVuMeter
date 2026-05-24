create a nice vu-meter for the cli  
you are not allowed to install any programs for the system  
python librtaries that do not change the system are allowed  
the target system has alsa and its tools installed

## project

`vu_meter/` package, stdlib only. Entry point: `./run.py` or `python3 -m vu_meter`.

### package structure

- `constants.py` - shared constants (sample rate, dB range, peak settings)
- `audio.py` - `AudioSource`, `AlsaSource`, `TestSource` + DSP helpers
- `display.py` - `PeakTracker`, `Renderer` (curses drawing)
- `meter.py` - `VUMeter` (orchestrator)
- `__main__.py` - arg parsing, entry point

### notes

- reads audio via `arecord` (ALSA) on target system
- `--test` flag runs with simulated audio (no hardware needed)
- `-D / --device` to select ALSA capture device
- curses display: L/R bars, color gradient, peak hold, dB scale
- development environment: Docker container without ALSA
