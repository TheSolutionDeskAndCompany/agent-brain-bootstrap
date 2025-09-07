# Agent Brain Bootstrap

## One‑Link Install (Windows)

Run in PowerShell to download and install the latest build (replace `ORG/REPO` after you tag and publish):

```
iwr -useb https://raw.githubusercontent.com/ORG/REPO/main/scripts/bootstrap.ps1 | iex
```

Accessible, voice‑driven developer assistant for Windows with iPhone/iPad or Android tablet over RDP. Built accessibility‑first for blind users using NVDA, Narrator, or TalkBack.

This repo wires up Goose (orchestration) + Ollama (local models) + AssemblyAI (STT) into a hands‑free workflow with Auto VAD, wake word, and audible beeps. Output is console‑only so your screen reader speaks it.

## Getting Started

Prereqs
- Windows 10/11, Python 3.10+
- Docker Desktop (for optional WordPress memory)
- Ollama installed with a local model (e.g., qwen2.5)

Setup
- Clone this repo and copy `.env.example` to `.env`
- Ensure `ASSEMBLYAI_API_KEY` is set in `.env`
- (Optional) Start WordPress: `docker compose up -d` (http://localhost:8080)

Start Agent (hands‑free)
- `./scripts/start_agent.ps1`
  - Default: Auto VAD, wake word `agent`, TTS OFF
  - Beeps on start/stop listening
  - Printout is read by NVDA/Narrator

Power options
- Set sensitivity: `./scripts/start_agent.ps1 -Threshold 1100`
- Disable wake word: `./scripts/start_agent.ps1 -WakeWord ''`
- PTT fallback: `./scripts/start_agent.ps1 -Mode ptt -NoTTS`
- Quick sanity: `./scripts/sanity_agent.ps1 -Mode auto -NoTTS`
- Status without starting: `./scripts/show_status.ps1`

## 📢 Voice Commands

➡️ [Voice Command Catalog](docs/voice-commands.md) — full list of supported commands,
tuning tips, and quick examples. Designed for NVDA/Narrator users.

## Accessibility Notes
- Use Microsoft Remote Desktop on iPhone/iPad or Android.
- In the RDP connection, set Sound = “Play on this device” and enable “Redirect microphone/Microphone”.
- In Windows Sound → Recording, verify “Remote Audio” shows input levels when speaking.
- iOS specifics: see `docs/ios-setup.md` for step‑by‑step setup and permissions.

## Configuration (env)
- `GOOSE_PROVIDER` (default: `ollama`)
- `OLLAMA_HOST` (default: `http://localhost:11434`)
- `OLLAMA_MODEL` (default: `qwen2.5`)
- `ASSEMBLYAI_API_KEY` (required for STT)
- `WP_BASE_URL`, `WP_JWT_TOKEN` (optional if using WordPress memory)
- `LOG_LEVEL` (default: `INFO`)

## Troubleshooting
- Triggers too often: raise `-Threshold` (1100–1500)
- Doesn’t trigger: lower to 700–800; check RDP mic levels
- Empty transcript: start speaking after the beep‑up and pause at the end
- STT 401: fix `ASSEMBLYAI_API_KEY` in `.env`, reopen shell

## License
MIT


## ?? Mobile & RDP Quick Start (iPhone / Amazon Fire)

Run locally
```bash
python -m pip install fastapi uvicorn pydantic
python mobile_server.py
```
Open: `http://<LAN-IP>:8000/public/mobile/index.html` on your phone/tablet.

One-tap RDP
```bash
python scripts/rdp_profile_generator.py --host <RDP_HOST> --username <USER>
# -> public/rdp/desktop.rdp
```
On your device, tap Connect to Desktop. The native RDP app opens and connects.

Hands-free (iPhone)
Use the Siri Shortcut recipe in `docs/ACCESSIBILITY.md`.

Accessibility
See `docs/ACCESSIBILITY.md` for VoiceOver/VoiceView usage, in-session screen readers, and best practices.
