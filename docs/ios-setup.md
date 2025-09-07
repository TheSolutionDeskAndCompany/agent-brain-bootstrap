# iPhone/iPad Setup (RDP to Windows)

These steps let an iPhone or iPad act as the mic/speaker for your Windows PC running the Agent. The wake word + beeps and console output are optimized for screen readers.

Prereqs
- Windows PC running this repo
- iPhone/iPad on the same network (or VPN)
- Microsoft Remote Desktop app from the App Store

Steps (on iOS)
1) Install Microsoft Remote Desktop (by Microsoft) from the App Store
2) Open the app → Add PC
   - PC Name: your Windows PC hostname or IP (e.g., 192.168.1.50)
   - User Account: your Windows username/password (or prompt on connect)
3) Connection settings → Devices & Audio
   - Microphone: ON (Redirect to PC)
   - Sound/Audio: Play on this device
   - Clipboard: ON (optional)
4) The app will prompt for microphone permission → Tap Allow
5) Connect

Steps (on Windows host)
- Win+R → `mmsys.cpl` → Recording → ensure “Remote Audio” is the Default device.
- Speak into the iPhone mic → verify the Remote Audio meter bounces.
- Optional: Playback tab → set “Remote Audio” as default playback so beeps route back to iPhone.

Run the agent (on Windows)
- Open PowerShell in the repo root:
  - `./scripts/start_agent.ps1`
- Listen for the status line and beep‑up/bee p‑down cues.
- Say commands prefixed with the wake word “agent …”.

Quick test phrases
- “agent open vs code”
- “agent create file demo\\hello.py with print('hi')”
- “agent read file demo\\hello.py”
- “agent repeat last”

Troubleshooting
- No mic input: In iOS Settings → Remote Desktop, ensure “Microphone” permission is enabled.
- No audio on iPhone: In the RDP app connection settings, ensure audio is set to Play on this device; turn up iPhone volume; disable Silent mode.
- Background noise: Run with higher threshold: `./scripts/start_agent.ps1 -Threshold 1200`.
- Not triggering: Lower threshold to 700–800; be sure to pause briefly after you finish speaking.
- Security: Never expose RDP directly to the internet. Use a VPN or secure tunnel.

Notes
- Beeps use Windows’ system beep (winsound); RDP routes it to the iPhone when audio redirection is enabled.
- Wake word (“agent”) reduces accidental triggers; you can disable it via `-WakeWord ''` for testing.
