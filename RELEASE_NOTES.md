# Baseline Accessibility Build

Tag: v0.1.0 (draft)
Title: Baseline Accessibility Build — Auto VAD + Wake Word + Beeps

Highlights
- Hands‑free default: Auto VAD with wake word “agent”, audible start/stop beeps
- PTT fallback: Enter to start/stop recording (optional)
- Status line: Printed at startup and via “agent status”
- Repeat last: “agent repeat last” reprints prior transcript/reply
- Logging: Per‑turn logs in `logs/agent.log`
- Scripts: `start_agent.ps1`, `sanity_agent.ps1`, `show_status.ps1`
- Docs: One‑page Voice Command Catalog (`docs/voice-commands.md`), updated README

What’s Included
- Auto VAD + wake word gating in `agent/speech/voice_loop.py`
- NVDA‑friendly status in `agent/agent_main.py`
- Simple logging and repeat‑last in `agent/agent_main.py`
- Accessibility defaults and PowerShell scripts under `scripts/`

Getting Started
- Ensure `.env` contains `ASSEMBLYAI_API_KEY`
- Start hands‑free: `./scripts/start_agent.ps1`
- Say: “agent open vs code”, then “agent repeat last”

Tuning
- Too sensitive → increase `-Threshold` (1100–1500)
- Not triggering → lower to 700–800 and confirm “Remote Audio” levels in `mmsys.cpl`
- Partial transcripts → increase `TAIL_SIL_MS` to 1000–1200 in `voice_loop.py`

Known Notes
- STT depends on network connectivity to AssemblyAI; use PTT mode if bandwidth is poor
- Beep fallback uses terminal bell on non‑Windows platforms

Change Summary
- Add: wake‑word gate, beeps, robust VAD and PTT helpers
- Add: repeat‑last + logging
- Add: scripts/sanity_agent.ps1, scripts/show_status.ps1
- Add: docs/voice-commands.md
- Update: README with accessibility‑first flow and docs link

Date: 2025‑09‑07
