# Voice Command Catalog

Use the wake word “agent …” before each command.
Default mode: Auto (VAD) with wake word `agent`, audible beeps on start/stop.
NVDA or Narrator will read all output in the console.

---

## Core Controls
- agent repeat last — Reprint last transcript + reply
- agent status — Reprint the startup status line
- agent help — Summarize top commands
- agent cancel — Cancel a pending action or confirmation

---

## Files & Folders
- agent create file demo\hello.py with print('hi')
- agent append to demo\notes.txt — todo: write tests
- agent read file demo\hello.py
- agent create folder demo\data
- agent list files in demo
- agent delete file demo\old.txt (asks for confirmation)
- agent delete folder demo\build (asks for confirmation)

---

## Python Projects
- agent make python project in C:\Users\me\Projects\demo
- agent pip install requests numpy
- agent run python demo\hello.py
- agent run tests (pytest if available)

---

## Git
- agent git init
- agent git status
- agent git add all and commit initial commit
- agent git branch feature-voice
- agent git log last 3

---

## Code Assistance
- agent explain error ModuleNotFoundError: foo
- agent summarize file demo\hello.py
- agent generate function add(a,b) in demo\math_utils.py
- agent insert below in demo\hello.py — print('done')
- agent find in file demo\hello.py — def main

---

## System Helpers
- agent set working directory to C:\Users\me\Projects\demo
- agent where am i
- agent show environment PYTHONPATH
- agent set environment FOO=bar (session only)

---

## Accessibility & Diagnostics
- agent audio device — Print current input device name/index
- agent set input device to 1
- agent raise threshold to 1200 (less sensitive)
- agent lower threshold to 800 (more sensitive)
- agent show last 5 logs — Tail `logs/agent.log`

---

## Tuning Tips
- Triggers too often → raise threshold (1100–1500).
- Doesn’t trigger → lower to 700–800, check “Remote Audio” input levels.
- Partial transcripts → increase `TAIL_SIL_MS` to 1000–1200 in `voice_loop.py`.
- Disable wake word → run with `-WakeWord ''`.

---

## Quick Examples
- “agent open vs code”
- “agent create file demo\hello.py with print('hi')”
- “agent read file demo\hello.py”
- “agent git init”
- “agent repeat last”

---

Last updated: 2025-09-07

