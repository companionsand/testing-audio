# Audio Testing Suite

Simple interactive audio tests for Raspberry Pi devices.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Verify setup
python setup_check.py

# Run tests
python test_audio.py
```

## Tests Included

1. **Recording** - Records 5 seconds from microphone
2. **Playback** - Plays back the recording
3. **Music** - Plays a generated melodic sample
4. **Wake Word** - Listens for "Porcupine" wake word (Picovoice)

## Requirements

- Python 3.8+
- Working microphone
- Working speaker
- Internet (for Picovoice activation on first run)
