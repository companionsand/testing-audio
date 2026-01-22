#!/usr/bin/env python3
"""
Comprehensive Audio Path Diagnostic

Tests ALL audio output paths by playing a tone and recording simultaneously.
Uses FFT to detect if the tone was captured by the mic (loopback test).

This can run REMOTELY without human feedback - it will tell you which paths work.

Usage:
    python test_audio_paths.py           # Run all tests
    python test_audio_paths.py --quick   # Quick test (plughw only)
    python test_audio_paths.py --verbose # Show detailed FFT analysis
"""

import subprocess
import sys
import os
import time
import tempfile
import threading
import argparse
from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np

# Try to import audio libraries
try:
    import sounddevice as sd
    import soundfile as sf
except ImportError:
    print("✗ Missing dependencies. Run: pip install sounddevice soundfile numpy")
    sys.exit(1)


# ============================================================
# Configuration
# ============================================================
SAMPLE_RATE = 48000        # Match ReSpeaker native rate
TONE_DURATION = 2.0        # seconds
RECORD_DURATION = 3.0      # seconds (longer to capture full tone)
TONE_AMPLITUDE = 0.8       # Volume of test tone
TEST_FREQUENCY = 1000      # Hz - easy to detect, not too harsh

# Detection thresholds
MIN_RMS_THRESHOLD = 0.001  # Minimum RMS to consider "signal present"
FREQ_TOLERANCE = 50        # Hz tolerance for frequency detection
SNR_THRESHOLD = 3.0        # Signal must be 3x above noise floor


# ============================================================
# Audio Path Definitions
# ============================================================
@dataclass
class AudioPath:
    """Definition of an audio output path to test"""
    name: str
    description: str
    aplay_device: Optional[str] = None      # For aplay -D <device>
    mpv_device: Optional[str] = None        # For mpv --audio-device=<device>
    sounddevice_device: Optional[str] = None # For sounddevice
    priority: int = 10                       # Lower = test first


# All paths to test (ordered by priority)
AUDIO_PATHS = [
    AudioPath(
        name="plughw_direct",
        description="Direct hardware (plughw:0,0) - bypasses all ALSA plugins",
        aplay_device="plughw:0,0",
        mpv_device="alsa/plughw:CARD=ArrayUAC10,DEV=0",
        priority=1
    ),
    AudioPath(
        name="hw_direct",
        description="Raw hardware (hw:0,0) - no conversion",
        aplay_device="hw:0,0",
        priority=2
    ),
    AudioPath(
        name="alsa_default",
        description="ALSA default - uses /etc/asound.conf chain",
        aplay_device="default",
        mpv_device="alsa",
        priority=3
    ),
    AudioPath(
        name="respeaker_out",
        description="ReSpeaker softvol chain (softvol -> plug -> dmix)",
        aplay_device="respeaker_out",
        priority=4
    ),
    AudioPath(
        name="respeaker_out_raw",
        description="ReSpeaker plug->dmix (no softvol)",
        aplay_device="respeaker_out_raw",
        priority=5
    ),
    AudioPath(
        name="respeaker_dmix",
        description="ReSpeaker dmix directly",
        aplay_device="respeaker_dmix",
        priority=6
    ),
    AudioPath(
        name="mpv_auto",
        description="mpv auto device selection",
        mpv_device="auto",
        priority=7
    ),
    AudioPath(
        name="sounddevice_default",
        description="Python sounddevice default output",
        sounddevice_device="default",
        priority=8
    ),
]


# ============================================================
# Utility Functions
# ============================================================

def generate_tone(frequency: float, duration: float, sample_rate: int, amplitude: float = 0.8) -> np.ndarray:
    """Generate a sine wave tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    # Add slight fade in/out to avoid clicks
    fade_samples = int(sample_rate * 0.05)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    tone = amplitude * envelope * np.sin(2 * np.pi * frequency * t)
    return tone.astype(np.float32)


def save_tone_wav(tone: np.ndarray, sample_rate: int, filepath: str):
    """Save tone to WAV file for aplay."""
    sf.write(filepath, tone, sample_rate, subtype='PCM_16')


def analyze_recording(recording: np.ndarray, sample_rate: int, expected_freq: float, verbose: bool = False) -> dict:
    """
    Analyze a recording to detect if the expected tone is present.
    
    Returns dict with:
        - rms: Overall RMS level
        - peak: Peak amplitude
        - detected_freq: Dominant frequency found
        - freq_magnitude: Magnitude at expected frequency
        - noise_floor: Average magnitude (noise)
        - snr: Signal-to-noise ratio
        - tone_detected: bool - was the tone found?
    """
    # Ensure mono
    if len(recording.shape) > 1:
        recording = recording[:, 0]
    
    # Basic stats
    rms = np.sqrt(np.mean(recording ** 2))
    peak = np.max(np.abs(recording))
    
    # FFT analysis
    n = len(recording)
    fft = np.fft.rfft(recording)
    freqs = np.fft.rfftfreq(n, 1/sample_rate)
    magnitudes = np.abs(fft) / n
    
    # Find dominant frequency
    dominant_idx = np.argmax(magnitudes[1:]) + 1  # Skip DC
    detected_freq = freqs[dominant_idx]
    
    # Get magnitude at expected frequency
    freq_idx = np.argmin(np.abs(freqs - expected_freq))
    freq_magnitude = magnitudes[freq_idx]
    
    # Calculate noise floor (average of magnitudes, excluding the tone region)
    tone_region_start = np.argmin(np.abs(freqs - (expected_freq - 100)))
    tone_region_end = np.argmin(np.abs(freqs - (expected_freq + 100)))
    noise_magnitudes = np.concatenate([magnitudes[:tone_region_start], magnitudes[tone_region_end:]])
    noise_floor = np.mean(noise_magnitudes) if len(noise_magnitudes) > 0 else 0.0001
    
    # Signal-to-noise ratio
    snr = freq_magnitude / noise_floor if noise_floor > 0 else 0
    
    # Detection criteria:
    # 1. RMS above threshold (something is playing)
    # 2. Detected frequency close to expected
    # 3. SNR above threshold (tone is distinct from noise)
    freq_match = abs(detected_freq - expected_freq) < FREQ_TOLERANCE
    tone_detected = (rms > MIN_RMS_THRESHOLD) and freq_match and (snr > SNR_THRESHOLD)
    
    result = {
        'rms': rms,
        'peak': peak,
        'detected_freq': detected_freq,
        'freq_magnitude': freq_magnitude,
        'noise_floor': noise_floor,
        'snr': snr,
        'tone_detected': tone_detected,
        'freq_match': freq_match,
    }
    
    if verbose:
        print(f"      RMS: {rms:.6f}, Peak: {peak:.4f}")
        print(f"      Expected freq: {expected_freq}Hz, Detected: {detected_freq:.1f}Hz")
        print(f"      Freq magnitude: {freq_magnitude:.6f}, Noise floor: {noise_floor:.6f}")
        print(f"      SNR: {snr:.2f}x (threshold: {SNR_THRESHOLD}x)")
    
    return result


def record_audio(duration: float, sample_rate: int, channels: int = 1) -> np.ndarray:
    """Record audio from default input device."""
    frames = int(duration * sample_rate)
    recording = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype=np.float32)
    sd.wait()
    return recording


# ============================================================
# Playback Methods
# ============================================================

def play_with_aplay(wav_path: str, device: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """Play WAV file using aplay with specified device."""
    cmd = ["aplay", "-D", device, wav_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def play_with_mpv(url_or_file: str, device: str, duration: float = 3.0) -> Tuple[bool, str]:
    """Play audio using mpv with specified device."""
    cmd = [
        "mpv",
        "--no-video",
        "--really-quiet",
        f"--audio-device={device}",
        f"--length={duration}",
        url_or_file
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 2)
        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr.strip()[:100]
    except subprocess.TimeoutExpired:
        return True, ""  # Timeout is expected for length limit
    except Exception as e:
        return False, str(e)


def play_with_sounddevice(tone: np.ndarray, sample_rate: int, device: Optional[str] = None) -> Tuple[bool, str]:
    """Play tone using sounddevice."""
    try:
        sd.play(tone, sample_rate, blocking=True)
        return True, ""
    except Exception as e:
        return False, str(e)


# ============================================================
# Test Runner
# ============================================================

def test_audio_path(path: AudioPath, tone: np.ndarray, wav_path: str, verbose: bool = False) -> dict:
    """
    Test a single audio path by playing tone and recording simultaneously.
    
    Returns dict with test results.
    """
    result = {
        'name': path.name,
        'description': path.description,
        'playback_ok': False,
        'playback_error': '',
        'tone_detected': False,
        'analysis': None,
    }
    
    # Determine which playback method to use
    if path.aplay_device:
        playback_method = 'aplay'
        playback_target = path.aplay_device
    elif path.mpv_device:
        playback_method = 'mpv'
        playback_target = path.mpv_device
    elif path.sounddevice_device:
        playback_method = 'sounddevice'
        playback_target = path.sounddevice_device
    else:
        result['playback_error'] = 'No playback device configured'
        return result
    
    print(f"\n  Testing: {path.name}")
    print(f"    Method: {playback_method}, Target: {playback_target}")
    
    # Start recording in background thread
    recording_result = {'data': None, 'error': None}
    
    def record_thread():
        try:
            recording_result['data'] = record_audio(RECORD_DURATION, SAMPLE_RATE, channels=1)
        except Exception as e:
            recording_result['error'] = str(e)
    
    recorder = threading.Thread(target=record_thread)
    recorder.start()
    
    # Small delay to ensure recording starts
    time.sleep(0.3)
    
    # Play the tone
    if playback_method == 'aplay':
        playback_ok, playback_error = play_with_aplay(wav_path, playback_target)
    elif playback_method == 'mpv':
        playback_ok, playback_error = play_with_mpv(wav_path, playback_target, TONE_DURATION + 1)
    elif playback_method == 'sounddevice':
        playback_ok, playback_error = play_with_sounddevice(tone, SAMPLE_RATE)
    
    # Wait for recording to finish
    recorder.join(timeout=RECORD_DURATION + 2)
    
    result['playback_ok'] = playback_ok
    result['playback_error'] = playback_error
    
    if not playback_ok:
        print(f"    ✗ Playback failed: {playback_error}")
        return result
    
    print(f"    ✓ Playback command succeeded")
    
    # Analyze the recording
    if recording_result['error']:
        print(f"    ✗ Recording failed: {recording_result['error']}")
        return result
    
    recording = recording_result['data']
    if recording is None or len(recording) == 0:
        print(f"    ✗ Recording is empty")
        return result
    
    print(f"    ✓ Recorded {len(recording)} samples")
    
    # Analyze
    analysis = analyze_recording(recording, SAMPLE_RATE, TEST_FREQUENCY, verbose=verbose)
    result['analysis'] = analysis
    result['tone_detected'] = analysis['tone_detected']
    
    if analysis['tone_detected']:
        print(f"    ✓ TONE DETECTED! (SNR: {analysis['snr']:.1f}x, freq: {analysis['detected_freq']:.0f}Hz)")
    else:
        reason = []
        if analysis['rms'] < MIN_RMS_THRESHOLD:
            reason.append(f"RMS too low ({analysis['rms']:.6f})")
        if not analysis['freq_match']:
            reason.append(f"Wrong freq ({analysis['detected_freq']:.0f}Hz)")
        if analysis['snr'] < SNR_THRESHOLD:
            reason.append(f"SNR too low ({analysis['snr']:.1f}x)")
        print(f"    ✗ Tone NOT detected: {', '.join(reason)}")
    
    return result


def run_all_tests(paths: List[AudioPath], verbose: bool = False) -> List[dict]:
    """Run tests on all audio paths."""
    print("=" * 60)
    print("COMPREHENSIVE AUDIO PATH DIAGNOSTIC")
    print("=" * 60)
    print()
    print(f"Test frequency: {TEST_FREQUENCY}Hz")
    print(f"Tone duration: {TONE_DURATION}s")
    print(f"Record duration: {RECORD_DURATION}s")
    print(f"Sample rate: {SAMPLE_RATE}Hz")
    print()
    
    # Generate test tone
    print("Generating test tone...")
    tone = generate_tone(TEST_FREQUENCY, TONE_DURATION, SAMPLE_RATE, TONE_AMPLITUDE)
    
    # Save to temp WAV file for aplay/mpv
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav_path = f.name
    save_tone_wav(tone, SAMPLE_RATE, wav_path)
    print(f"Saved test tone to: {wav_path}")
    
    # Check available devices
    print("\nChecking audio devices...")
    print(f"  Input devices: {sd.query_devices(kind='input')['name']}")
    print(f"  Output devices: {sd.query_devices(kind='output')['name']}")
    
    # Sort paths by priority
    sorted_paths = sorted(paths, key=lambda p: p.priority)
    
    results = []
    for path in sorted_paths:
        try:
            result = test_audio_path(path, tone, wav_path, verbose=verbose)
            results.append(result)
        except Exception as e:
            print(f"\n  ✗ Error testing {path.name}: {e}")
            results.append({
                'name': path.name,
                'description': path.description,
                'playback_ok': False,
                'playback_error': str(e),
                'tone_detected': False,
                'analysis': None,
            })
    
    # Cleanup
    try:
        os.unlink(wav_path)
    except:
        pass
    
    return results


def print_summary(results: List[dict]):
    """Print summary table of results."""
    print("\n")
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"{'Path':<25} {'Playback':<10} {'Tone Detected':<15} {'SNR':<10}")
    print("-" * 60)
    
    working_paths = []
    
    for r in results:
        playback_status = "✓" if r['playback_ok'] else "✗"
        
        if r['tone_detected']:
            tone_status = "✓ YES"
            snr = f"{r['analysis']['snr']:.1f}x" if r['analysis'] else "-"
            working_paths.append(r['name'])
        else:
            tone_status = "✗ NO"
            snr = "-"
        
        print(f"{r['name']:<25} {playback_status:<10} {tone_status:<15} {snr:<10}")
    
    print()
    print("=" * 60)
    
    if working_paths:
        print(f"✓ WORKING PATHS: {', '.join(working_paths)}")
        print()
        print("RECOMMENDATION:")
        if 'plughw_direct' in working_paths:
            print("  Use plughw:0,0 for reliable playback.")
            print("  For mpv: --audio-device=alsa/plughw:CARD=ArrayUAC10,DEV=0")
            print("  For aplay: aplay -D plughw:0,0")
        elif 'alsa_default' in working_paths:
            print("  ALSA default chain works. Apps should work normally.")
        else:
            print(f"  Use: {working_paths[0]}")
    else:
        print("✗ NO WORKING PATHS DETECTED!")
        print()
        print("TROUBLESHOOTING:")
        print("  1. Check physical speaker connection")
        print("  2. Verify ALSA card index: aplay -l")
        print("  3. Check if speaker/amp is powered")
        print("  4. Try: speaker-test -D hw:0,0 -c 2 -t sine")
    
    print("=" * 60)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Comprehensive Audio Path Diagnostic')
    parser.add_argument('--quick', action='store_true', help='Quick test (plughw only)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed FFT analysis')
    args = parser.parse_args()
    
    # Select paths to test
    if args.quick:
        paths = [p for p in AUDIO_PATHS if p.name == 'plughw_direct']
    else:
        paths = AUDIO_PATHS
    
    # Run tests
    results = run_all_tests(paths, verbose=args.verbose)
    
    # Print summary
    print_summary(results)
    
    # Exit code: 0 if any path works, 1 if none work
    working = any(r['tone_detected'] for r in results)
    return 0 if working else 1


if __name__ == "__main__":
    sys.exit(main())
