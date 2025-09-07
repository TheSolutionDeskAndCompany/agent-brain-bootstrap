import requests, sys
from agent.config.settings import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from agent.utils.logger import get_logger
log = get_logger("speech_test")
TEXT = "Hello! This is your agent brain speaking from Windows."
def main():
    if not (ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID):
        print("Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID"); sys.exit(1)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    r = requests.post(url, headers={"xi-api-key": ELEVENLABS_API_KEY, "accept":"audio/mpeg","content-type":"application/json"}, json={"text": TEXT}, timeout=120)
    r.raise_for_status()
    with open("out.wav","wb") as f: f.write(r.content)
    log.info("Wrote out.wav (MPEG container). Play it to confirm sound.")
if __name__ == "__main__": main()
