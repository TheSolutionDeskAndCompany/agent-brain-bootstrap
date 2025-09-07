# Agent Brain — Production-Ready Plan (Windows + iPhone Controller)
_Last updated: 2025-09-07_

This plan gets you to a one-link install for a blind user on Windows, plus a mobile controller from iPhone with near-zero setup.

## 0) What "one-link" means
You will host a short PowerShell command (a "bootstrap" link) in your repo’s README and/or a short vanity URL. When the user runs it in Windows PowerShell, it:
- Downloads the latest installer from GitHub Releases.
- Installs the Agent as a background app (auto-start on login), creates a desktop shortcut, and adds a Start Menu entry.
- Opens an Accessible Web Controller (served locally) with huge buttons that can be used from iPhone on the same Wi‑Fi—or via Tailscale for remote access.

## 6) One-Link Bootstrap Command (Windows)
```
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb https://raw.githubusercontent.com/ORG/REPO/main/scripts/bootstrap.ps1 | iex"
```

