#!/usr/bin/env python3
"""
Setup check script - verifies all dependencies and audio devices are working.
Run this first before test_audio.py
"""

import sys

def check_import(name: str, package: str = None) -> bool:
    """Try importing a module and report success/failure."""
    package = package or name
    try:
        __import__(name)
        print(f"✓ {package}")
        return True
    except ImportError as e:
        print(f"✗ {package} - {e}")
        return False

def main():
    print("=" * 50)
    print("Audio Test Setup Check")
    print("=" * 50)
    
    # Check all required imports
    print("\n1. Checking dependencies...")
    all_ok = True
    all_ok &= check_import("sounddevice")
    all_ok &= check_import("soundfile")
    all_ok &= check_import("numpy")
    all_ok &= check_import("pvporcupine")
    
    if not all_ok:
        print("\n⚠ Some dependencies missing.")
        print("   If using virtual environment: source venv/bin/activate && pip install -r requirements.txt")
        print("   Or run: bash setup.sh (creates venv and installs dependencies)")
        sys.exit(1)
    
    # Check audio devices
    print("\n2. Checking audio devices...")
    import sounddevice as sd
    
    # List input devices
    print("\nInput devices (microphones):")
    inputs = [d for d in sd.query_devices() if d['max_input_channels'] > 0]
    if inputs:
        for d in inputs:
            marker = "→" if d['index'] == sd.default.device[0] else " "
            print(f"  {marker} [{d['index']}] {d['name']} ({d['max_input_channels']} ch)")
    else:
        print("  ✗ No input devices found!")
        all_ok = False
    
    # List output devices
    print("\nOutput devices (speakers):")
    outputs = [d for d in sd.query_devices() if d['max_output_channels'] > 0]
    if outputs:
        for d in outputs:
            marker = "→" if d['index'] == sd.default.device[1] else " "
            print(f"  {marker} [{d['index']}] {d['name']} ({d['max_output_channels']} ch)")
    else:
        print("  ✗ No output devices found!")
        all_ok = False
    
    # Quick audio test
    print("\n3. Quick audio sanity check...")
    import numpy as np
    import warnings
    try:
        # Generate a very short test tone
        sr = 16000
        duration = 0.1
        t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
        tone = 0.3 * np.sin(2 * np.pi * 440 * t)
        # Note: May show harmless callback cleanup warning with Python 3.13
        sd.play(tone, sr, blocking=True)
        print("  ✓ Audio output working (played short beep)")
    except Exception as e:
        print(f"  ✗ Audio output failed: {e}")
        all_ok = False
    
    # Check Porcupine
    print("\n4. Checking Picovoice Porcupine...")
    try:
        import pvporcupine
        # Just check we can get keywords - don't create instance yet
        keywords = pvporcupine.KEYWORDS
        print(f"  ✓ Porcupine available, built-in keywords: {', '.join(keywords)}")
    except Exception as e:
        print(f"  ✗ Porcupine check failed: {e}")
        all_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_ok:
        print("✓ All checks passed! Ready to run test_audio.py")
    else:
        print("✗ Some checks failed. Fix issues above before running tests.")
        sys.exit(1)

if __name__ == "__main__":
    main()
