import sounddevice as sd

print("=== Audio Devices ===")
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

print("\nRun this script with: python list_devices.py")
