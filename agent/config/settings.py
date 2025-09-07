import os
from dotenv import load_dotenv
load_dotenv()

GOOSE_PROVIDER = os.getenv("GOOSE_PROVIDER", "ollama")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

WP_BASE_URL = os.getenv("WP_BASE_URL", "http://localhost:8080")
WP_JWT_TOKEN = os.getenv("WP_JWT_TOKEN", "")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
