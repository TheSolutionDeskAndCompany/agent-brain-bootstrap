import os
import time
import argparse
import logging
import sounddevice as sd
from agent.memory.wp_client import get_latest_brain_post
from agent.decision_engine import respond
from agent.speech.voice_loop import run_voice_loop, AssemblyAIClient
from agent.utils.logger import get_logger

log = get_logger("agent_main")

# Simple file logging and repeat-last support
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "agent.log")

_last_transcript = None  # type: ignore
_last_reply = None       # type: ignore
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

def generate_text(user_text: str) -> str:
    """Generate a response to the user's input using the decision engine."""
    try:
        global _last_transcript, _last_reply

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

        brain = get_latest_brain_post()
        mood = (brain.get("acf") or {}).get("agent_emotions")
        persona = (brain.get("acf") or {}).get("agent_personality")
        reply = respond(user_text, mood=mood, persona=persona)

        # Save last + log the interaction
        _last_transcript = user_text
        _last_reply = reply
        log_line("YOU", user_text)
        log_line("AGENT", reply)

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
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Check for AssemblyAI API key
    if not os.getenv("ASSEMBLYAI_API_KEY"):
        log.error("ASSEMBLYAI_API_KEY environment variable not set")
        print("\nError: ASSEMBLYAI_API_KEY environment variable is required.")
        print("Please set it in your .env file or environment variables.")
        print("You can get a free API key at https://app.assemblyai.com/signup")
        return
    
    # Spoken-friendly status line for screen readers
    def _device_name(idx):
        try:
            if idx is None:
                return 'default'
            return sd.query_devices(idx)['name']
        except Exception:
            return 'default input'

    status = (
        f"[status] Mode: {args.mode.upper()}  | Wake word: "
        f"{args.wake_word or 'OFF'}  | TTS: OFF  | Model: qwen2.5 via Goose  | "
        f"Input: {_device_name(args.device)}"
    )
    print(status)

    try:
        log.info(f"Starting agent in {args.mode} mode" + (" (No TTS)" if args.no_tts else ""))
        log.info("Speak to interact with the agent")
        log.info("Press Ctrl+C to exit")

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

    # initialize runtime state
    RUNTIME_STATE.update({
        "mode": args.mode,
        "wake_word": (args.wake_word or None),
        "threshold": args.threshold,
        "device": args.device,
    })

    STATUS_LINE = build_status()
    print(STATUS_LINE)

        run_voice_loop(
            generate_text=generate_text,
            mode=args.mode,
            no_tts=args.no_tts,
            device=args.device,
            threshold=args.threshold,
            wake_word=(args.wake_word or None),
            state=RUNTIME_STATE,
        )
        
    except KeyboardInterrupt:
        log.info("Shutting down...")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
