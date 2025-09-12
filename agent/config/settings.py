import os
from dotenv import load_dotenv

load_dotenv()

try:
    import keyring  # optional secure storage
except Exception:  # pragma: no cover - keyring optional
    keyring = None  # type: ignore


def _secret(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    if v:
        return v
    if keyring:
        try:
            s = keyring.get_password("agent-brain", name)
            if s:
                return s
        except Exception:
            pass
    return default


GOOSE_PROVIDER = os.getenv("GOOSE_PROVIDER", "ollama")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")
GEMINI_API_KEY = _secret("GEMINI_API_KEY", "")

WP_BASE_URL = os.getenv("WP_BASE_URL", "http://localhost:8080")
WP_JWT_TOKEN = _secret("WP_JWT_TOKEN", "")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = _secret("WP_APP_PASSWORD", "")

ASSEMBLYAI_API_KEY = _secret("ASSEMBLYAI_API_KEY", "")
ELEVENLABS_API_KEY = _secret("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
