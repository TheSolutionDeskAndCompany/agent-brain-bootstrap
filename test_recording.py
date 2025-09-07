import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import time

def test_recording():
    # Audio settings
    duration = 3  # seconds
    sample_rate = 44100
    channels = 1
    input_device = 6  # Senary Audio capture
    output_device = 5  # AMD HD Audio HDMI out
    
    print("=== Audio Recording Test ===")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Channels: {channels}")
    print(f"Device: {sd.query_devices(device)['name']}")
    
    # Record audio
    print("\nRecording for 3 seconds... Speak into your microphone.")
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        device=input_device,
        dtype='int16'  # 16-bit PCM
    )
    
    # Show recording progress
    for i in range(3, 0, -1):
        print(f"Recording... {i}")
        time.sleep(1)
    
    sd.wait()  # Wait until recording is finished
    
    # Save as WAV file
    filename = 'test_recording.wav'
    wav.write(filename, sample_rate, recording)
    
    # Print file info
    print(f"\nSaved to {filename}")
    print(f"File size: {len(recording) * 2 / 1024:.1f} KB")
    print(f"Duration: {len(recording) / sample_rate:.2f} seconds")
    
    # Playback the recording
    print("\nPlaying back recording...")
    sd.play(recording, sample_rate, device=output_device)
    sd.wait()
    print("Playback complete!")

if __name__ == "__main__":
    test_recording()
