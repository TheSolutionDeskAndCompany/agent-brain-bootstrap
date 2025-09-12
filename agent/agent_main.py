import os
import time
import json
import re
import argparse
import logging
import sounddevice as sd
from threading import Thread
from agent import server as controller_server
from agent.memory.wp_client import get_latest_brain_post
from agent.decision_engine import respond
from agent.speech.voice_loop import run_voice_loop, AssemblyAIClient
from agent.utils.logger import get_logger

log = get_logger("agent_main")

# Simple file logging and repeat-last support
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "agent.log")
SETTINGS_PATH = os.path.join(LOG_DIR, "settings.json")
HISTORY_PATH = os.path.join(LOG_DIR, "history.json")

_last_transcript = None  # type: ignore
_last_reply = None       # type: ignore
_history: list[tuple[str, str]] = []
_macros: list[tuple[re.Pattern[str], str]] = []
STATUS_LINE = ""         # set in main()
RUNTIME_STATE = {
    "mode": None,
    "wake_word": None,
    "threshold": None,
    "device": None,
}

def log_line(kind: str, text: str) -> None:
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {kind}: {text}\n")
    except Exception:
        # Don't break runtime if logging fails
        pass

def _load_settings() -> dict:
    try:
        if os.path.isfile(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}

def _save_settings(data: dict) -> None:
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def _load_history(limit: int = 20) -> list[tuple[str, str]]:
    try:
        if os.path.isfile(HISTORY_PATH):
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                items = json.load(f) or []
                out = []
                for it in items[-limit:]:
                    if isinstance(it, list) and len(it) == 2:
                        out.append((str(it[0]), str(it[1])))
                return out
    except Exception:
        pass
    return []

def _save_history(hist: list[tuple[str, str]], limit: int = 50) -> None:
    try:
        items = hist[-limit:]
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _load_macros() -> list[tuple[re.Pattern[str], str]]:
    paths = [
        os.path.join(os.path.dirname(__file__), 'config', 'macros.json'),
        os.path.join(LOG_DIR, 'macros.json'),  # user override
    ]
    rules: list[tuple[re.Pattern[str], str]] = []
    for p in paths:
        try:
            if os.path.isfile(p):
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f) or []
                for item in data:
                    m = str(item.get('match') or '').strip()
                    r = str(item.get('rewrite') or '').strip()
                    if not m or not r:
                        continue
                    rules.append((re.compile(m, re.IGNORECASE), r))
        except Exception:
            continue
    return rules

def reload_macros_from_files() -> int:
    """Reload macros from config and logs folders. Returns count."""
    global _macros
    _macros = _load_macros()
    return len(_macros)

def generate_text(user_text: str) -> str:
    """Generate a response to the user's input using the decision engine."""
    try:
        global _last_transcript, _last_reply, _history

        # Handle built-in commands locally (no model call)
        t_norm = (user_text or "").strip().lower()
        if t_norm in ("agent repeat", "agent repeat last", "repeat last", "repeat"):
            if _last_transcript or _last_reply:
                return (
                    "[repeat] Previous transcript:\n"
                    + f"[you ] {_last_transcript or ''}\n"
                    + "[repeat] Previous reply:\n"
                    + f"[agent] {_last_reply or ''}"
                )
            return "[repeat] Nothing to repeat yet."

        if t_norm in ("agent status", "status"):
            return build_status()

        if t_norm in ("agent help", "help"):
            return (
                "[help] Say 'agent status' | 'agent repeat last' | "
                "'set threshold to 1100' | 'disable wake word'.\n"
                "[help] You can also say 'agent history last 5' or 'agent audio device' or 'agent save settings'.\n"
                "[help] Custom macros: edit agent/config/macros.json or logs/macros.json and say 'agent reload macros'."
            )

        # History: 'agent history last N' or 'agent history'
        import re as _re
        m = _re.match(r"^(?:agent\s+)?history(?:\s+last\s+(\d+))?$", t_norm)
        if m:
            try:
                n = int(m.group(1)) if m.group(1) else 5
            except Exception:
                n = 5
            items = _history[-n:]
            if not items:
                return "[history] No interactions yet."
            lines = ["[history] Recent interactions:"]
            for i, (q, a) in enumerate(items, 1):
                lines.append(f"{i}. you: {q}")
                lines.append(f"   agent: {a}")
            return "\n".join(lines)

        if t_norm in ("agent save settings", "save settings"):
            try:
                s = _load_settings()
                s.update({
                    "wake_word": RUNTIME_STATE.get("wake_word"),
                    "threshold": RUNTIME_STATE.get("threshold"),
                    "device": RUNTIME_STATE.get("device"),
                })
                _save_settings(s)
                return "[settings] Saved current settings to settings.json"
            except Exception:
                return "[settings] Failed to save settings"

        if t_norm in ("agent reload macros", "reload macros"):
            try:
                global _macros
                _macros = _load_macros()
                return f"[macros] Reloaded {_macros and len(_macros) or 0} macro(s)"
            except Exception:
                return "[macros] Failed to reload macros"

        if t_norm in ("agent audio device", "audio device"):
            try:
                idx = RUNTIME_STATE.get("device")
                name = 'default'
                if idx is not None:
                    name = sd.query_devices(idx)['name']
                else:
                    name = sd.query_devices(None)['name']
                return f"[audio] Input device: {name} (index={idx if idx is not None else 'default'})"
            except Exception:
                return "[audio] Input device: default"

        # Apply macros (regex rewrite) before fetching memory or calling model
        text_for_model = user_text
        for pat, rep in (_macros or []):
            m = pat.match(user_text)
            if m:
                try:
                    text_for_model = pat.sub(rep, user_text)
                except Exception:
                    text_for_model = user_text
                break

        brain = get_latest_brain_post()
        mood = (brain.get("acf") or {}).get("agent_emotions")
        persona = (brain.get("acf") or {}).get("agent_personality")
        reply = respond(text_for_model, mood=mood, persona=persona)

        # Save last + log the interaction
        _last_transcript = user_text
        _last_reply = reply
        log_line("YOU", user_text)
        log_line("AGENT", reply)
        _history.append((user_text, reply))
        if len(_history) > 20:
            _history = _history[-20:]
        _save_history(_history, limit=50)

        return reply
    except Exception as e:
        log.error(f"Error generating response: {e}", exc_info=True)
        return f"I encountered an error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Agent Brain - Voice Interface')
    parser.add_argument('--mode', choices=['ptt', 'auto'], default='auto',
                      help='Interaction mode: ptt (push-to-talk) or auto (VAD). Default: auto')
    parser.add_argument('--no-tts', action='store_true', default=True,
                      help='Disable TTS output (console only). Default: enabled (no TTS)')
    parser.add_argument('--wake-word', type=str, default='agent',
                      help="Wake word to gate commands in auto/PTT (e.g., 'agent'). Empty to disable.")
    parser.add_argument('--device', type=int, default=None,
                      help='Audio device index (use list_devices.py to find)')
    parser.add_argument('--threshold', type=int, default=900,
                      help='Voice activation threshold (auto mode). Default: 900')
    parser.add_argument('--calibrate', action='store_true',
                      help='Run a short mic calibration to suggest a threshold, then exit')
    parser.add_argument('--apply', action='store_true',
                      help='When used with --calibrate, automatically save the suggested threshold')
    parser.add_argument('--no-settings', action='store_true',
                      help='Ignore persisted settings.json values')
    parser.add_argument('--save-settings', action='store_true',
                      help='Persist current threshold/wake word/device to settings.json and exit')
    parser.add_argument('--calibrate', action='store_true',
                      help='Run a short mic calibration to suggest a threshold, then exit')
    
    args = parser.parse_args()
    
    # Set up logging (console via basicConfig already in get_logger)
    # Add rotating file handler for agent.log
    try:
        from logging.handlers import RotatingFileHandler
        fh_present = any(isinstance(h, RotatingFileHandler) for h in log.handlers)
        if not fh_present:
            fh = RotatingFileHandler(LOG_PATH, maxBytes=512*1024, backupCount=3, encoding='utf-8')
            fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S'))
            log.addHandler(fh)
            log.setLevel(logging.INFO)
    except Exception:
        pass
    
    # Load history for continuity
    try:
        global _history, _macros
        _history = _load_history(20)
        _macros = _load_macros()
    except Exception:
        pass

    # Check for AssemblyAI API key
    if not os.getenv("ASSEMBLYAI_API_KEY"):
        log.error("ASSEMBLYAI_API_KEY environment variable not set")
        print("\nError: ASSEMBLYAI_API_KEY environment variable is required.")
        print("Please set it in your .env file or environment variables.")
        print("You can get a free API key at https://app.assemblyai.com/signup")
        return
    # Optional: quick mic calibration
    if args.calibrate:
        try:
            print("\n[calibrate] Sampling ambient audio for 2 seconds...")
            import numpy as _np
            dur_s = 2.0
            sr = 16000
            n = int(sr * dur_s)
            data = sd.rec(n, samplerate=sr, channels=1, dtype='int16', device=args.device)
            sd.wait()
            x = data.reshape(-1).astype(_np.int32)
            rms = float((_np.sqrt(_np.mean((x * x)))))
            # Suggest threshold as 2.5x ambient RMS, clamped
            rec = int(max(600, min(2000, rms * 2.5)))
            print(f"[calibrate] Ambient RMS ~ {rms:.1f} -> suggested Threshold ~ {rec}")
            if args.apply:
                s = _load_settings()
                s.update({"threshold": rec})
                _save_settings(s)
                print(f"[calibrate] Saved to settings.json (threshold={rec})")
            else:
                ans = input("[calibrate] Save this threshold for future runs? [y/N] ").strip().lower()
                if ans == 'y':
                    s = _load_settings()
                    s.update({"threshold": rec})
                    _save_settings(s)
                    print(f"[calibrate] Saved to settings.json (threshold={rec})")
                else:
                    print("[calibrate] Not saved. You can run again with --apply to save automatically.")
        except Exception as e:
            log.error(f"Calibration failed: {e}")
            print(f"[calibrate] Error: {e}")
        return
    try:
        log.info(f"Starting agent in {args.mode} mode" + (" (No TTS)" if args.no_tts else ""))
        log.info("Speak to interact with the agent")
        log.info("Press Ctrl+C to exit")
        print("[help] Say 'agent status' or 'agent repeat last'.")
        print("[help] Adjust sensitivity with 'set threshold to 1100' or change wake word.")

        # Spoken-friendly status line for screen readers
        global STATUS_LINE, RUNTIME_STATE

        def _device_name(idx):
            try:
                if idx is None:
                    return 'default'
                return sd.query_devices(idx)['name']
            except Exception:
                return 'default input'

        def build_status() -> str:
            ww = RUNTIME_STATE.get("wake_word")
            th = RUNTIME_STATE.get("threshold")
            mode = (RUNTIME_STATE.get("mode") or args.mode).upper()
            inp = _device_name(RUNTIME_STATE.get("device"))
            return (
                f"[status] Mode: {mode}  | Wake word: {ww or 'OFF'}  | TTS: OFF  | "
                f"Model: qwen2.5 via Goose  | Input: {inp}  | Threshold: {th}"
            )

        # Initialize runtime state (apply persisted settings if present and not overridden)
        settings = {} if args.no_settings else _load_settings()
        wake_word = args.wake_word
        threshold = args.threshold
        device = args.device
        if not args.no_settings:
            try:
                if wake_word == 'agent' and settings.get('wake_word'):
                    wake_word = settings.get('wake_word')
                if threshold == 900 and isinstance(settings.get('threshold'), int):
                    threshold = int(settings.get('threshold'))
                if device is None and settings.get('device') is not None:
                    device = int(settings.get('device'))
            except Exception:
                pass

        RUNTIME_STATE.update({
            "mode": args.mode,
            "wake_word": (wake_word or None),
            "threshold": threshold,
            "device": device,
        })

        STATUS_LINE = build_status()
        print(STATUS_LINE)

        if args.save_settings:
            s = _load_settings()
            s.update({
                "wake_word": RUNTIME_STATE.get("wake_word"),
                "threshold": RUNTIME_STATE.get("threshold"),
                "device": RUNTIME_STATE.get("device"),
            })
            _save_settings(s)
            print("[settings] Saved current settings to settings.json. Exiting.")
            return

        # Start controller server in background
        try:
            Thread(target=controller_server.run, daemon=True).start()
            log.info("Controller server running at http://localhost:8765/controller")
        except Exception as e:
            log.error(f"Failed to start controller server: {e}")

        run_voice_loop(
            generate_text=generate_text,
            mode=args.mode,
            no_tts=args.no_tts,
            device=RUNTIME_STATE.get("device"),
            threshold=RUNTIME_STATE.get("threshold"),
            wake_word=RUNTIME_STATE.get("wake_word"),
            state=RUNTIME_STATE,
        )

    except KeyboardInterrupt:
        log.info("Shutting down...")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
