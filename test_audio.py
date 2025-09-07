import sounddevice as sd
import numpy as np

def list_audio_devices():
    print("\n=== Audio Devices ===")
    print("\nInput Devices:")
    for i in range(len(sd.query_devices())):
        dev = sd.query_devices(i)
        if dev['max_input_channels'] > 0:
            print(f"{i}: {dev['name']} (Input)")

    print("\nOutput Devices:")
    for i in range(len(sd.query_devices())):
        dev = sd.query_devices(i)
        if dev['max_output_channels'] > 0:
            print(f"{i}: {dev['name']} (Output)")

def test_record_playback(input_device=1, output_device=4, duration=3):
    print(f"\n=== Testing Audio (Input: {input_device}, Output: {output_device}) ===")
    
    # Record
    print(f"\nRecording for {duration} seconds...")
    try:
        recording = sd.rec(
            int(duration * 44100),
            samplerate=44100,
            channels=1,
            device=input_device,
            dtype='float32'
        )
        sd.wait()
        print("Recording complete!")
    except Exception as e:
        print(f"Error during recording: {e}")
        return
    
    # Playback
    print("Playing back...")
    try:
        sd.play(recording, samplerate=44100, device=output_device)
        sd.wait()
        print("Playback complete!")
    except Exception as e:
        print(f"Error during playback: {e}")

if __name__ == "__main__":
    list_audio_devices()
    
    # Try with default devices first
    test_record_playback()
    
    # Let user try different devices
    while True:
        print("\n=== Test Different Devices ===")
        try:
            input_dev = input("Input device number (or press Enter to quit): ")
            if not input_dev:
                break
                
            output_dev = input("Output device number: ")
            if not output_dev:
                break
                
            test_record_playback(
                input_device=int(input_dev),
                output_device=int(output_dev)
            )
        except ValueError:
            print("Please enter valid device numbers.")
        except Exception as e:
            print(f"Error: {e}")
