# Audio Testing Suite

Comprehensive audio diagnostic and testing tools for Raspberry Pi devices.

## Quick Start

```bash
# Run setup script (creates venv and installs dependencies)
bash setup.sh

# Activate virtual environment
source venv/bin/activate

# Verify setup
python setup_check.py

# Run tests
python test_audio.py
```

**Note:** On Raspberry Pi (Debian), you must use a virtual environment due to externally-managed Python.

## Scripts

### `test_audio_paths.py` - **Comprehensive Audio Diagnostic**
Tests ALL audio output paths and verifies speaker is working via loopback test.
**Can run remotely without human feedback.**

```bash
python test_audio_paths.py           # Test all paths
python test_audio_paths.py --quick   # Quick test (plughw only)
python test_audio_paths.py --verbose # Detailed FFT analysis
```

### `test_audio.py` - Interactive Walkthrough
Step-by-step audio test with user prompts.

```bash
python test_audio.py
# Override ALSA device:
ALSA_DEVICE=plughw:0,0 python test_audio.py
```

### `test_radio.py` - Radio Stream Test
Tests continuous audio playback via mpv.

```bash
python test_radio.py              # Play default station
python test_radio.py --list       # List stations
python test_radio.py 2            # Play station #2
python test_radio.py --device alsa/plughw:CARD=ArrayUAC10,DEV=0
```

## Tests Included

1. **Recording** - Records from microphone
2. **Playback** - Plays back recording via aplay
3. **Music** - Plays generated melodic sample
4. **Wake Word** - Listens for "Porcupine" (Picovoice)
5. **Audio Path Diagnostic** - Tests all ALSA paths with loopback verification

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALSA_DEVICE` | ALSA device for playback | `plughw:0,0` |
| `AUDIO_DEVICE` | mpv audio device | `alsa/plughw:CARD=ArrayUAC10,DEV=0` |

## Troubleshooting

If audio isn't working:
1. Run `python test_audio_paths.py` to identify working paths
2. Check card index: `aplay -l`
3. Test direct hardware: `aplay -D plughw:0,0 /usr/share/sounds/alsa/Front_Center.wav`

## Requirements

- Python 3.8+
- Working microphone
- Working speaker
- mpv (for radio test)
- Internet (for Picovoice activation on first run)
