import subprocess
from agent.utils.logger import get_logger

log = get_logger("decision_engine")


def goose_prompt(prompt: str) -> str:
    """Run Goose CLI safely with args list (no shell)."""
    try:
        proc = subprocess.run(
            ["goose", "run", prompt],
            check=True,
            capture_output=True,
            text=True,
        )
        return (proc.stdout or "").strip()
    except FileNotFoundError:
        log.error("Goose CLI not found on PATH. Install or configure Goose.")
        return "Decision engine unavailable: Goose CLI not installed."
    except subprocess.CalledProcessError as e:
        log.error(f"Goose failed (exit {e.returncode}): {e.stderr or e.stdout}")
        return "I hit an error in the decision engine."


def respond(user_text: str, mood=None, persona=None) -> str:
    mood_tag = f"[mood={mood}]" if mood else ""
    persona_tag = f"[persona={persona}]" if persona else ""
    prompt = f"{persona_tag}{mood_tag} USER: {user_text}\nASSISTANT:"
    return goose_prompt(prompt)
