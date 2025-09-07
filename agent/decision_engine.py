import subprocess, shlex
from agent.utils.logger import get_logger
log = get_logger("decision_engine")
def goose_prompt(prompt: str) -> str:
    cmd = f'goose run "{prompt}"'
    try:
        out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        log.error(f"Goose failed: {e.output}")
        return "I hit an error in the decision engine."
def respond(user_text: str, mood=None, persona=None) -> str:
    mood_tag = f"[mood={mood}]" if mood else ""
    persona_tag = f"[persona={persona}]" if persona else ""
    prompt = f"{persona_tag}{mood_tag} USER: {user_text}\nASSISTANT:"
    return goose_prompt(prompt)
