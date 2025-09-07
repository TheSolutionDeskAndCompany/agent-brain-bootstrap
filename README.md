<<<<<<< HEAD
# Agent Brain Bootstrap 🧠

An AI Agent Brain environment for Windows PCs, orchestrated with Goose.
Built with accessibility-first design so it works equally well for sighted developers and blind users (using TalkBack, NVDA, or Narrator).

👉 **If you are using a screen reader, please see [README-ACCESSIBLE.md](README-ACCESSIBLE.md) for the step-by-step accessible guide.**

## 📑 Table of Contents
- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Accessibility](#-accessibility)
- [Configuration Reference](#-configuration-reference)
- [Advanced Usage](#-advanced-usage)
- [Troubleshooting](#-troubleshooting)
- [Security Notes](#-security-notes)
- [Contributing](#-contributing)
- [License](#-license)

## 📝 Overview
Agent Brain Bootstrap is a modular AI assistant stack.
It connects local AI models, speech input/output, and memory storage into one system that can be controlled remotely.

- **Core**: Goose orchestrates models and extensions.
- **Reasoning**: Ollama runs local models (Qwen2.5 by default).
- **Memory**: WordPress holds configs, emotions, and episodic memory.
- **Speech**: AssemblyAI handles speech-to-text, ElevenLabs handles text-to-speech.
- **Remote Control**: Access the Windows PC from an Android tablet via RDP, with full audio and mic redirection.

## ✨ Features
- 🧩 **Goose orchestrator** — tool calling and reasoning
- ⚡ **Ollama integration** — run open-source models locally
- 🗂 **WordPress backend** — edit personality, memory, configs
- 🗣 **Speech-first workflow** — STT + TTS loop for blind users
- ♿ **Accessible by design** — TalkBack, NVDA, Narrator friendly
- 📡 **Remote control** — Android tablet + RDP with audio/mic pass-through
- 🔌 **Extensible** — add MCP containers for GitHub, Brave, Slack, etc.

## 🏗 Architecture
```
(Android Tablet) 
   | TalkBack + RDP (audio + mic)
   v
(Windows PC) 
   ├─ Goose (orchestrator)
   │    ├─ Ollama/Gemini (models)
   │    ├─ WordPress/Firebase (memory/configs)
   │    ├─ MCP Containers (tools: GitHub, Brave, etc.)
   │    └─ AssemblyAI (STT) → ElevenLabs (TTS)
   v
Spoken audio response → back to tablet
```

## 🚀 Quick Start
1. **Clone**
   ```powershell
   git clone https://github.com/<your-org>/<your-repo>.git
   cd agent-brain-bootstrap
   copy .env.example .env
   ```

2. **Start WordPress**
   ```powershell
   docker compose up -d
   ```
   - WordPress: http://localhost:8080
   - Install plugins: Advanced Custom Fields (ACF) + JWT Auth
   - Import fields from `wp/acf-export.json`

3. **Run Ollama + Goose**
   ```powershell
   ollama run qwen2.5
   pip install gooseai --upgrade
   goose configure
   ```
   - Provider: Ollama
   - Host: http://localhost:11434
   - Model: qwen2.5

4. **Test Speech**
   ```powershell
   python -m venv .venv
   . \.venv\Scripts\Activate.ps1
   pip install -r agent/requirements.txt
   python agent/speech/test_speech.py
   ```
   - This creates `out.wav` with a test message

5. **Run Agent**
   ```powershell
   python agent/agent_main.py
   ```

## 🔊 Accessibility
Android tablet with TalkBack connects to Windows PC via Microsoft Remote Desktop (RDP).
In RDP connection settings:
- Sound → Play on this device
- Microphone → Redirect microphone

This ensures:
- NVDA/Narrator voices are heard on the tablet
- Tablet mic input reaches the Windows PC
- All agent replies are spoken out loud with ElevenLabs TTS

👉 For the full accessible walkthrough, see [README-ACCESSIBLE.md](README-ACCESSIBLE.md).

## ⚙️ Configuration Reference
| Variable | Description |
|----------|-------------|
| `GOOSE_PROVIDER` | Which provider to use (`ollama`, `gemini`) |
| `OLLAMA_HOST` | Host for Ollama (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Local model to run (default: `qwen2.5`) |
| `GEMINI_API_KEY` | Optional fallback cloud model key |
| `WP_BASE_URL` | WordPress base URL (default: `http://localhost:8080`) |
| `WP_JWT_TOKEN` | WordPress JWT authentication token |
| `WP_USERNAME` | WordPress username (if using App Password auth) |
| `WP_APP_PASSWORD` | WordPress application password |
| `ASSEMBLYAI_API_KEY` | API key for AssemblyAI (speech-to-text) |
| `ELEVENLABS_API_KEY` | API key for ElevenLabs (text-to-speech) |
| `ELEVENLABS_VOICE_ID` | Voice ID to use for ElevenLabs |
| `LOG_LEVEL` | Logging level (default: `INFO`) |

## 🔧 Advanced Usage
### Adding MCP Containers
You can run additional MCP containers alongside Goose. Example for GitHub and Brave search:

```yaml
services:
  mcp-github:
    image: ghcr.io/metorial/mcp-container--modelcontextprotocol--servers--github:latest
    ports: ["7101:3000"]
    environment:
      GITHUB_TOKEN: ${GITHUB_TOKEN}

  mcp-brave:
    image: ghcr.io/metorial/mcp-container--modelcontextprotocol--servers--brave-search:latest
    ports: ["7102:3000"]
```

Then add them in Goose with:
```
goose configure → Add Extension → Remote Extension
```

## 🛠 Troubleshooting
- **No audio?** → Check RDP connection sound = Play on this device.
- **Mic not working?** → Ensure RDP mic redirection is enabled.
- **Goose not connecting?** → Verify Ollama is running on http://localhost:11434.
- **WordPress errors?** → Re-import ACF JSON, confirm JWT plugin is active.

## 🔒 Security Notes
- Do not expose RDP to the internet. Use a VPN for remote access.
- Rotate API keys regularly.
- Back up WordPress volumes if using for long-term memory.

## 🤝 Contributing
1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m "Add feature"`
4. Push and open a Pull Request

Please keep contributions accessible — include alt text, semantic headings, and clear steps.

## 📜 License
MIT License © 2025 The Solution Desk


# Agent Brain – Accessible Setup Guide

## Table of Contents
1. [What You'll Have](#what-youll-have)
2. [Setup the Android Tablet](#setup-the-android-tablet)
3. [Prepare the Windows PC](#prepare-the-windows-pc)
4. [Download the Bootstrap Repo](#download-the-bootstrap-repo)
5. [Start WordPress (Memory Layer)](#start-wordpress-memory-layer)
6. [Install Goose + Ollama](#install-goose--ollama)
7. [Test Speech](#test-speech)
8. [Run the Agent](#run-the-agent)
9. [RDP Audio and Microphone Redirection](#rdp-audio-and-microphone-redirection)
10. [Troubleshooting](#troubleshooting)
11. [Safety Notes](#safety-notes)

## What You'll Have
A Windows PC running the "Agent Brain" with:
- Goose (AI orchestration)
- Ollama (local models like Qwen2.5)
- WordPress (stores memory, emotions, personality)
- AssemblyAI (speech-to-text)
- ElevenLabs (text-to-speech)

## Setup the Android Tablet
1. Install Microsoft Remote Desktop from the Play Store
2. Open the app → Add a PC
3. PC name: type the local IP or hostname of your Windows PC
4. User account: enter your Windows username and password
5. Save and connect
6. TalkBack will announce "Connect button" - double-tap to connect

## Prepare the Windows PC
1. Log in and enable your screen reader:
   - Narrator: Windows + Ctrl + Enter
   - Or install NVDA from nvaccess.org (recommended)
2. Install Docker Desktop from docker.com/products/docker-desktop
3. Install Python 3.10 or later from python.org

## Download the Bootstrap Repo
1. Open PowerShell
2. Run these commands:
   ```powershell
   git clone <repo_url> agent-brain-bootstrap
   cd agent-brain-bootstrap
   copy .env.example .env
   ```
3. Edit .env with your API keys using Notepad or another text editor

## Start WordPress (Memory Layer)
1. From PowerShell in the repo folder:
   ```powershell
   docker compose up -d
   ```
2. Wait 30-60 seconds
3. In your browser, go to: http://localhost:8080
4. Complete WordPress setup (screen reader will read the fields)
5. In WordPress:
   - Install "Advanced Custom Fields" plugin
   - Install "JWT Authentication for WP REST API" plugin
   - Import `wp/acf-export.json` from the repo

## Install Goose + Ollama
1. Install Ollama from ollama.ai/download
2. Run:
   ```powershell
   ollama run qwen2.5
   ```
3. Install Goose:
   ```powershell
   pip install gooseai --upgrade
   goose configure
   ```
4. During configuration, use these settings:
   - Provider: Ollama
   - Host: http://localhost:11434
   - Model: qwen2.5

## Test Speech
1. Create a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r agent/requirements.txt
   ```
2. Run the speech test:
   ```powershell
   python agent/speech/test_speech.py
   ```
3. This creates `out.wav` which should contain speech

## Run the Agent
1. Activate the virtual environment if not already active:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. Start the agent:
   ```powershell
   python agent/agent_main.py
   ```
3. Speak into your microphone (see RDP setup below)

## RDP Audio and Microphone Redirection
### On Windows PC (host)
1. Press Windows + R
2. Type: `sysdm.cpl` and press Enter
3. Go to the Remote tab
4. Check "Allow remote connections to this computer"
5. Check "Allow connections only from computers running Remote Desktop with Network Level Authentication"
6. Click OK

### On Android Tablet (RDP app)
1. Open Microsoft Remote Desktop
2. Edit your PC connection
3. Under "Sound" select "Play on this device"
4. Enable "Redirect microphone"
5. Save and connect

## Troubleshooting
- If mic doesn't work:
  - Disconnect RDP session
  - Edit connection and re-toggle "Redirect microphone"
  - Check Windows Sound settings for "Remote Audio" input device
- For audio latency:
  - Use headphones with TalkBack
  - Select "Play on this device only" in RDP audio settings

## Safety Notes
- Never expose RDP directly to the internet
- Use a VPN for remote access
- Rotate API keys regularly
- Back up the WordPress volume for important memories



## Live Voice Loop
- PTT mode (recommended over RDP):
```powershell
.\scripts\start_agent.ps1 -Mode ptt
```
- Auto mode (experimental VAD):
```powershell
.\scripts\start_agent.ps1 -Mode auto
```

=======
# agent-brain-bootstrap
Accessible voice-driven developer assistant for Windows, Fire Tablet + screen readers.  Bootstrap project integrating Goose, Ollama, and ElevenLabs.
>>>>>>> origin/main
