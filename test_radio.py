#!/usr/bin/env python3
"""
Radio Stream Test - Tests continuous audio playback via mpv

Usage:
    python test_radio.py              # Play default station (Jazz)
    python test_radio.py 1            # Play station by number
    python test_radio.py --list       # List available stations
    python test_radio.py --device X   # Use specific audio device

Environment Variables:
    AUDIO_DEVICE - Override default audio device (e.g., "alsa/plughw:CARD=ArrayUAC10,DEV=0")

Press Ctrl+C to stop playback.
"""

import subprocess
import shutil
import sys
import signal
import time
import os

# ============================================================
# Audio Device Configuration
# ============================================================
# Default: use plughw for ReSpeaker (bypasses broken ALSA chains)
# Set AUDIO_DEVICE env var to override, or use --device flag
DEFAULT_AUDIO_DEVICE = "alsa/plughw:CARD=ArrayUAC10,DEV=0"


def get_audio_device() -> str:
    """Get audio device from env var or default."""
    return os.environ.get("AUDIO_DEVICE", DEFAULT_AUDIO_DEVICE)

# ============================================================
# Reliable Radio Stations (verified working streams)
# ============================================================
STATIONS = [
    {"name": "Jazz Radio (France)", "url": "http://jazz-wr04.ice.infomaniak.ch/jazz-wr04-128.mp3"},
    {"name": "Classical (WQXR)", "url": "https://stream.wqxr.org/wqxr"},
    {"name": "Lofi Hip Hop", "url": "https://streams.fluxfm.de/Chillhop/mp3-320/streams.fluxfm.de/"},
    {"name": "BBC Radio 1", "url": "http://stream.live.vc.bbcmedia.co.uk/bbc_radio_one"},
    {"name": "Ambient/Drone", "url": "http://ice6.somafm.com/dronezone-128-mp3"},
    {"name": "Chillout", "url": "http://ice4.somafm.com/groovesalad-128-mp3"},
]


def check_mpv() -> bool:
    """Check if mpv is installed."""
    return shutil.which("mpv") is not None


def list_stations():
    """List all available stations."""
    print("\n" + "=" * 50)
    print("AVAILABLE STATIONS")
    print("=" * 50)
    print()
    for i, station in enumerate(STATIONS, 1):
        print(f"  [{i}] {station['name']}")
    print()
    print("Usage: python test_radio.py <number>")
    print("=" * 50)


def play_station(index: int = 0, audio_device: str = None):
    """Play a radio station using mpv."""
    if index < 0 or index >= len(STATIONS):
        print(f"✗ Invalid station number. Use 1-{len(STATIONS)}")
        sys.exit(1)
    
    station = STATIONS[index]
    device = audio_device or get_audio_device()
    
    print("\n" + "=" * 50)
    print("RADIO STREAM TEST")
    print("=" * 50)
    print()
    print(f"  Station: {station['name']}")
    print(f"  URL: {station['url']}")
    print(f"  Audio device: {device}")
    print()
    print("  Starting stream... (Press Ctrl+C to stop)")
    print()
    
    # Start mpv with explicit audio device
    # --no-video: audio only
    # --really-quiet: suppress most output
    # --audio-device: force specific ALSA device (bypasses broken chains)
    process = subprocess.Popen(
        [
            "mpv",
            "--no-video",
            "--really-quiet",
            f"--audio-device={device}",
            station["url"]
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n  Stopping...")
        process.terminate()
        process.wait()
        print("  ✓ Stopped")
        print()
        print("=" * 50)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wait for process
    print("  🎵 Playing... (you should hear audio)")
    print()
    
    # Check if stream started successfully
    time.sleep(2)
    if process.poll() is not None:
        print("  ✗ Stream failed to start!")
        print("    Check your internet connection or try another station.")
        sys.exit(1)
    
    print("  ✓ Stream active")
    print()
    print("  If you hear nothing, check:")
    print("    - Speaker volume")
    print("    - Audio output device (aplay -l)")
    print("    - ALSA config")
    print()
    
    # Keep running until interrupted
    try:
        process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)


def main():
    # Check mpv
    if not check_mpv():
        print("✗ mpv not found!")
        print()
        print("Install mpv:")
        print("  Mac:   brew install mpv")
        print("  Linux: sudo apt install mpv")
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    audio_device = None
    station_index = 0
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ("--list", "-l"):
            list_stations()
            return
        elif arg in ("--help", "-h"):
            print(__doc__)
            return
        elif arg in ("--device", "-d"):
            if i + 1 < len(args):
                audio_device = args[i + 1]
                i += 1
            else:
                print("✗ --device requires an argument")
                sys.exit(1)
        elif arg.isdigit():
            station_index = int(arg) - 1
        else:
            print(f"Unknown argument: {arg}")
            print("Use --help for usage")
            sys.exit(1)
        i += 1
    
    play_station(station_index, audio_device)


if __name__ == "__main__":
    main()
