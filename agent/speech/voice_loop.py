# agent/speech/voice_loop.py
# Auto-VOX (voice activity) without webrtcvad — works on Windows w/ Python 3.12
# Dependencies: sounddevice, numpy, scipy, requests

from __future__ import annotations
import os, io, time, math, tempfile, threading, queue, contextlib
from typing import Callable, Optional
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write
import requests

# Make webrtcvad optional
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    webrtcvad = None
    VAD_AVAILABLE = False

from agent.utils.logger import get_logger

log = get_logger("voice_loop")

# Constants
# ----------- Config defaults (tune if needed) -----------
SR = 16000                  # sample rate
BLOCK_MS = 30               # frame size (ms)
THRESHOLD = 600             # energy threshold to start (0-32767). Raise in noisy rooms.
MIN_TALK_MS = 200           # must exceed threshold for at least this to start
TAIL_SIL_MS = 800           # stop after this much silence
MAX_UTTER_MS = 8000         # hard stop length cap per turn
# --------------------------------------------------------

AAI_KEY_ENV = "ASSEMBLYAI_API_KEY"

class AssemblyAIClient:
    def __init__(self, api_key: Optional[str]=None):
        self.api_key = api_key or os.getenv(AAI_KEY_ENV)
        if not self.api_key:
            raise RuntimeError(f"{AAI_KEY_ENV} not set")

    def _headers(self, content_type: Optional[str]=None):
        h = {"authorization": self.api_key}
        if content_type: h["content-type"] = content_type
        return h

    def upload(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            r = requests.post("https://api.assemblyai.com/v2/upload",
                              headers=self._headers(), data=f)
        r.raise_for_status()
        return r.json()["upload_url"]

    def transcribe_url(self, url: str, poll_ms: int=800) -> str:
        r = requests.post("https://api.assemblyai.com/v2/transcript",
                          headers=self._headers("application/json"),
                          json={"audio_url": url})
        r.raise_for_status()
        tid = r.json()["id"]
        while True:
            s = requests.get(f"https://api.assemblyai.com/v2/transcript/{tid}",
                             headers=self._headers())
            s.raise_for_status()
            j = s.json()
            if j["status"] == "completed":
                return (j.get("text") or "").strip()
            if j["status"] == "error":
                raise RuntimeError(j.get("error","transcription failed"))
            time.sleep(poll_ms/1000.0)

def _save_wav_int16(audio: np.ndarray, sr: int=SR) -> str:
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wav_write(path, sr, audio)
    return path

def assemblyai_transcribe_wav(wav_bytes: bytes) -> str:
    """Transcribe WAV audio bytes using AssemblyAI."""
    if not ASSEMBLYAI_API_KEY or ASSEMBLYAI_API_KEY == "your_assemblyai_api_key_here":
        print("\n[ERROR] AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY in .env")
        print("You can get a free API key at https://app.assemblyai.com/signup")
        return ""
    
    try:
        headers = {"authorization": ASSEMBLYAI_API_KEY}
        
        # Upload the audio file
        print("\n[STT] Uploading audio to AssemblyAI...")
        upload_response = requests.post(
            "https://api.assemblyai.com/v2/upload", 
            headers=headers, 
            data=wav_bytes
        )
        upload_response.raise_for_status()
        upload_url = upload_response.json()["upload_url"]
        
        # Start transcription
        print("[STT] Starting transcription...")
        transcribe_response = requests.post(
            "https://api.assemblyai.com/v2/transcripts",
            headers={**headers, "content-type": "application/json"},
            json={"audio_url": upload_url}
        )
        transcribe_response.raise_for_status()
        transcript_id = transcribe_response.json()["id"]
        
        # Poll for results
        print("[STT] Waiting for transcription...")
        for _ in range(30):  # Wait up to 24 seconds (0.8s * 30)
            time.sleep(0.8)
            status_response = requests.get(
                f"https://api.assemblyai.com/v2/transcripts/{transcript_id}",
                headers=headers,
                timeout=60
            )
            status_response.raise_for_status()
            data = status_response.json()
            
            if data.get("status") == "completed":
                text = data.get("text", "").strip()
                if text:
                    print("[STT] Transcription successful!")
                    return text
                return ""
                
            if data.get("status") == "error":
                error = data.get("error", "Unknown error")
                print(f"[STT] Transcription failed: {error}")
                return ""
        
        print("[STT] Transcription timed out")
        return ""
        
    except requests.exceptions.RequestException as e:
        print(f"[STT] API request failed: {e}")
        return ""

def listen_once_auto(device: Optional[int]=None,
                     threshold: int=THRESHOLD,
                     min_talk_ms: int=MIN_TALK_MS,
                     tail_sil_ms: int=TAIL_SIL_MS,
                     max_utter_ms: int=MAX_UTTER_MS) -> np.ndarray:
    """Blocks until it hears speech, returns one utterance as int16 audio."""
    print(f"[listen] Waiting for speech… threshold={threshold}, device={device}")
    audio = _record_utterance(
        device=device,
        threshold=threshold,
        min_talk_ms=min_talk_ms,
        tail_sil_ms=tail_sil_ms,
        max_utter_ms=max_utter_ms
    )
    dur = len(audio)/SR
    print(f"[listen] Captured {dur:.2f}s of audio")
    return audio

def stt_transcribe(audio: np.ndarray, aai: Optional[AssemblyAIClient]=None) -> str:
    aai = aai or AssemblyAIClient()
    wav_path = _save_wav_int16(audio, SR)
    try:
        print("[stt] Uploading…")
        url = aai.upload(wav_path)
        print("[stt] Transcribing…")
        text = aai.transcribe_url(url)
        print(f"[stt] Text: {text!r}")
        return text
    finally:
        with contextlib.suppress(Exception):
            os.remove(wav_path)

def run_voice_loop(
    generate_text: Callable[[str], str],
    mode: str = "ptt",
    no_tts: bool = False
) -> None:
    """Run the main voice interaction loop.
    
    Args:
        generate_text: Function that processes user text and returns response
        mode: 'ptt' for push-to-talk or 'auto' for voice activity detection
        no_tts: If True, only print responses instead of using TTS
    """
    log.info(f"Starting voice loop in {mode} mode" + (" (No TTS)" if no_tts else ""))
    
    try:
        while True:
            try:
                if mode == "ptt":
                    print("\n[PTT] Press Enter to speak (press Enter again to stop)...")
                    input()  # Wait for first Enter
                    
                    # Record audio
                    print("[PTT] Recording... Press Enter to stop.")
                    audio_data = record_ptt()
                    
                    # Convert to WAV and transcribe
                    wav_bytes = _wav_bytes_from_pcm16(audio_data)
                    try:
                        user_text = assemblyai_transcribe_wav(wav_bytes)
                        if not user_text:
                            print("[PTT] No speech detected. Please try again.")
                            continue
                            
                        print(f"[PTT] You said: {user_text}")
                        
                        # Process the command
                        response = generate_text(user_text)
                        print(f"[agent] {response}")
                        
                    except Exception as e:
                        print(f"[PTT] Error in speech recognition: {e}")
                    
                    # Only use TTS if not in NoTTS mode
                    if not no_tts and response:
                        # TODO: Add TTS call here if needed
                        pass
                        
                elif mode == "auto":
                    audio_data = listen_once_auto()
                    user_text = stt_transcribe(audio_data)
                    print(f"[stt] You said: {user_text}")
                    
                    response = generate_text(user_text)
                    print(f"[agent] {response}")
                    
                    if not no_tts and response:
                        # TODO: Add TTS call here if needed
                        pass
                    
            except KeyboardInterrupt:
                log.info("Loop interrupted by user")
                break
            except Exception as e:
                log.error(f"Error in voice loop: {e}", exc_info=True)
                
    except Exception as e:
        log.error(f"Fatal error in voice loop: {e}", exc_info=True)
    finally:
        log.info("Voice loop stopped")
