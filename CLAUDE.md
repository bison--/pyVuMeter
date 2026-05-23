create a nice vu-meter for the cli  
you are not allowed to install any programs for the system  
python librtaries that do not change the system are allowed  
the target system has alsa and its tools installed

## project

`vu_meter.py` - single-file CLI VU meter, stdlib only  
- reads audio via `arecord` (ALSA) on target system  
- `--test` flag runs with simulated audio (no hardware needed)  
- `-D / --device` to select ALSA capture device  
- curses display: L/R bars, color gradient, peak hold, dB scale  
- development environment: Docker container without ALSA
