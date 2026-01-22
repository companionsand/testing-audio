#!/usr/bin/env python3
"""
Interactive audio test walkthrough.
Tests: recording, playback, wake word detection (Porcupine)

Environment Variables:
    ALSA_DEVICE - ALSA device for playback (default: plughw:0,0)
"""

import sys
import time
import os
import subprocess
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
import pvporcupine

# ============================================================
# Configuration
# ============================================================
PICOVOICE_KEY = "cdrf4+EvCTDAqM3o7MQnZhrC9HyzIpgEtqqKKQ8jWzMDwT+tvtljZA=="
SAMPLE_RATE = 16000  # Porcupine requires 16kHz
RECORD_DURATION = 5  # seconds for test recording
RECORDING_FILE = "test_recording.wav"

# ALSA device for playback - use plughw to bypass broken ALSA chains
# Override with ALSA_DEVICE env var if needed
ALSA_PLAYBACK_DEVICE = os.environ.get("ALSA_DEVICE", "plughw:0,0")


# ============================================================
# Sound Generation Utilities
# ============================================================

def generate_chime(sr: int = 16000) -> np.ndarray:
    """
    Generate a pleasant success chime sound.
    Two-note ascending arpeggio (C5 → E5 → G5).
    """
    notes = [523.25, 659.25, 783.99]  # C5, E5, G5
    note_duration = 0.15
    
    chime = np.array([], dtype=np.float32)
    for freq in notes:
        t = np.linspace(0, note_duration, int(sr * note_duration), dtype=np.float32)
        # Sine wave with envelope (fade in/out)
        envelope = np.sin(np.pi * t / note_duration)
        note = 0.4 * envelope * np.sin(2 * np.pi * freq * t)
        chime = np.concatenate([chime, note])
    
    return chime


def generate_music_sample(sr: int = 16000, duration: float = 3.0) -> np.ndarray:
    """
    Generate a simple melodic sample (ascending scale with harmony).
    """
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    
    # Base melody: simple ascending pattern
    melody_freqs = [262, 294, 330, 349, 392, 440, 494, 523]  # C4 to C5
    samples_per_note = len(t) // len(melody_freqs)
    
    audio = np.zeros_like(t)
    for i, freq in enumerate(melody_freqs):
        start = i * samples_per_note
        end = start + samples_per_note
        if end > len(t):
            end = len(t)
        segment = t[start:end] - t[start]
        # Add main note + fifth harmony
        envelope = np.sin(np.pi * np.linspace(0, 1, end - start))
        audio[start:end] = envelope * (
            0.3 * np.sin(2 * np.pi * freq * segment) +
            0.15 * np.sin(2 * np.pi * freq * 1.5 * segment)  # fifth
        )
    
    return audio.astype(np.float32)


# ============================================================
# Test Steps
# ============================================================

def wait_for_enter(prompt: str = "Press ENTER to continue..."):
    """Wait for user to press enter."""
    input(f"\n{prompt}")


def play_with_aplay(wav_path: str, device: str = None) -> bool:
    """
    Play audio using aplay with explicit ALSA device.
    This bypasses potentially broken ALSA chains (dmix/softvol).
    """
    device = device or ALSA_PLAYBACK_DEVICE
    try:
        result = subprocess.run(
            ["aplay", "-D", device, wav_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    aplay error: {e}")
        return False


def play_tone_with_aplay(tone: np.ndarray, sample_rate: int, device: str = None) -> bool:
    """
    Generate tone and play via aplay.
    Saves to temp WAV, plays, then cleans up.
    """
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_path = f.name
    
    try:
        sf.write(temp_path, tone, sample_rate, subtype='PCM_16')
        return play_with_aplay(temp_path, device)
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


def step_record():
    """Step 1: Record audio from microphone."""
    print("\n" + "=" * 50)
    print("STEP 1: Recording Test")
    print("=" * 50)
    print(f"\nWe will record {RECORD_DURATION} seconds of audio.")
    print("Say something or make a sound!")
    
    wait_for_enter("Press ENTER to start recording...")
    
    print(f"\n🎤 Recording for {RECORD_DURATION} seconds...")
    try:
        # Record audio
        recording = sd.rec(
            int(RECORD_DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype=np.float32
        )
        sd.wait()
        
        # Save to file
        sf.write(RECORDING_FILE, recording, SAMPLE_RATE)
        print(f"✓ Recording saved to {RECORDING_FILE}")
        return True
    except Exception as e:
        print(f"✗ Recording failed: {e}")
        return False


def step_playback():
    """Step 2: Play back the recording."""
    print("\n" + "=" * 50)
    print("STEP 2: Playback Test")
    print("=" * 50)
    print("\nWe will now play back what you just recorded.")
    print(f"Using ALSA device: {ALSA_PLAYBACK_DEVICE}")
    
    wait_for_enter("Press ENTER to play recording...")
    
    print("\n🔊 Playing recording...")
    try:
        # Use aplay with explicit device (bypasses broken ALSA chains)
        success = play_with_aplay(RECORDING_FILE, ALSA_PLAYBACK_DEVICE)
        if success:
            print("✓ Playback complete")
            return True
        else:
            print("✗ Playback failed (aplay returned error)")
            return False
    except Exception as e:
        print(f"✗ Playback failed: {e}")
        return False


def step_play_music():
    """Step 3: Play a generated music sample."""
    print("\n" + "=" * 50)
    print("STEP 3: Music Playback Test")
    print("=" * 50)
    print("\nWe will play a generated melodic sample.")
    print(f"Using ALSA device: {ALSA_PLAYBACK_DEVICE}")
    
    wait_for_enter("Press ENTER to play music...")
    
    print("\n🎵 Playing music sample...")
    try:
        music = generate_music_sample(SAMPLE_RATE, duration=3.0)
        # Use aplay with explicit device (bypasses broken ALSA chains)
        success = play_tone_with_aplay(music, SAMPLE_RATE, ALSA_PLAYBACK_DEVICE)
        if success:
            print("✓ Music playback complete")
            return True
        else:
            print("✗ Music playback failed (aplay returned error)")
            return False
    except Exception as e:
        print(f"✗ Music playback failed: {e}")
        return False


def step_wake_word():
    """Step 4: Test wake word detection with Porcupine."""
    print("\n" + "=" * 50)
    print("STEP 4: Wake Word Detection Test")
    print("=" * 50)
    print("\nWe will listen for the wake word 'Porcupine'.")
    print("Say 'Porcupine' to trigger detection.")
    print("(Press Ctrl+C to skip after 30 seconds)")
    
    wait_for_enter("Press ENTER to start listening...")
    
    porcupine = None
    stream = None
    
    try:
        # Initialize Porcupine
        porcupine = pvporcupine.create(
            access_key=PICOVOICE_KEY,
            keywords=["porcupine"]
        )
        
        frame_length = porcupine.frame_length  # typically 512 samples
        
        print(f"\n👂 Listening for 'Porcupine'... (30 second timeout)")
        print("   Frame length: {}, Sample rate: {}".format(frame_length, porcupine.sample_rate))
        
        # Create audio buffer
        audio_buffer = []
        detected = False
        start_time = time.time()
        timeout = 30  # seconds
        
        def audio_callback(indata, frames, time_info, status):
            """Callback to collect audio frames."""
            if status:
                print(f"   Audio status: {status}")
            # Convert to int16 as required by Porcupine
            audio_buffer.extend(indata[:, 0].tolist())
        
        # Start audio stream
        stream = sd.InputStream(
            samplerate=porcupine.sample_rate,
            channels=1,
            dtype=np.float32,
            blocksize=frame_length,
            callback=audio_callback
        )
        stream.start()
        
        # Process audio frames
        while time.time() - start_time < timeout:
            # Wait for enough samples
            if len(audio_buffer) >= frame_length:
                # Get frame and convert to int16
                frame = np.array(audio_buffer[:frame_length])
                audio_buffer = audio_buffer[frame_length:]
                
                # Convert float32 to int16
                frame_int16 = (frame * 32767).astype(np.int16)
                
                # Process with Porcupine
                keyword_index = porcupine.process(frame_int16)
                
                if keyword_index >= 0:
                    print("\n🎉 Wake word 'Porcupine' detected!")
                    detected = True
                    break
            else:
                time.sleep(0.01)
        
        stream.stop()
        
        if detected:
            # Play success chime via aplay (bypasses broken ALSA chains)
            print("   Playing success chime...")
            chime = generate_chime(SAMPLE_RATE)
            play_tone_with_aplay(chime, SAMPLE_RATE, ALSA_PLAYBACK_DEVICE)
            print("✓ Wake word test passed!")
            return True
        else:
            print("\n⏱ Timeout - no wake word detected")
            return False
            
    except KeyboardInterrupt:
        print("\n   Skipped by user")
        return False
    except Exception as e:
        print(f"✗ Wake word test failed: {e}")
        return False
    finally:
        if stream:
            stream.close()
        if porcupine:
            porcupine.delete()


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 50)
    print("       AUDIO TEST WALKTHROUGH")
    print("=" * 50)
    print("\nThis script will walk you through 4 audio tests:")
    print("  1. Record audio from microphone")
    print("  2. Play back the recording")
    print("  3. Play a music sample")
    print("  4. Test wake word detection (Porcupine)")
    
    results = {}
    
    # Run each step
    results["1. Recording"] = step_record()
    results["2. Playback"] = step_playback()
    results["3. Music"] = step_play_music()
    results["4. Wake Word"] = step_wake_word()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("✓ All tests passed!" if all_passed else "⚠ Some tests failed"))
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
