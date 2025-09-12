# agent/speech/voice_loop.py
# Auto-VOX (voice activity) without webrtcvad — works on Windows w/ Python 3.12
# Dependencies: sounddevice, numpy, requests

from __future__ import annotations
import os, io, time, math, tempfile, threading, queue, contextlib, wave
from typing import Callable, Optional
import numpy as np
import sounddevice as sd
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

# Audible beeps for accessible cues
import sys, re
try:
    import winsound  # type: ignore
    _HAS_WINSOUND = True
except Exception:
    winsound = None  # type: ignore
    _HAS_WINSOUND = False

def _beep(freq: int = 800, ms: int = 120) -> None:
    try:
        if _HAS_WINSOUND and hasattr(winsound, "Beep") and sys.platform.startswith("win"):
            winsound.Beep(int(freq), int(ms))
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass

def _cue_start():
    _beep(1320, 100)

def _cue_end():
    _beep(880, 120)

def _normalize(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^\w\s']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _extract_after_wake(text: str, wake: Optional[str]) -> Optional[str]:
    if not wake:
        return text
    t = _normalize(text)
    w = _normalize(wake)
    if not w:
        return text
    if t == w:
        return ""
    if t.startswith(w + " "):
        return t[len(w) + 1:].strip()
    return None

# Constants
# ----------- Config defaults (tune if needed) -----------
SR = 16000                  # sample rate
BLOCK_MS = 30               # frame size (ms)
THRESHOLD = 900             # energy threshold to start (0-32767). Raise in noisy rooms.
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
        self._session = requests.Session()

    def _headers(self, content_type: Optional[str]=None):
        h = {"authorization": self.api_key}
        if content_type: h["content-type"] = content_type
        return h

    def upload(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            r = self._session.post(
                "https://api.assemblyai.com/v2/upload",
                headers=self._headers(),
                data=f,
                timeout=60,
            )
        r.raise_for_status()
        return r.json()["upload_url"]

    def transcribe_url(self, url: str, poll_ms: int=800) -> str:
        r = self._session.post(
            "https://api.assemblyai.com/v2/transcript",
            headers=self._headers("application/json"),
            json={"audio_url": url},
            timeout=30,
        )
        r.raise_for_status()
        tid = r.json()["id"]
        while True:
            s = self._session.get(
                f"https://api.assemblyai.com/v2/transcript/{tid}",
                headers=self._headers(),
                timeout=30,
            )
            s.raise_for_status()
            j = s.json()
            if j["status"] == "completed":
                return (j.get("text") or "").strip()
            if j["status"] == "error":
                raise RuntimeError(j.get("error","transcription failed"))
            time.sleep(poll_ms/1000.0)

def _save_wav_int16(audio: np.ndarray, sr: int=SR) -> str:
    """Save mono int16 audio to a temporary WAV file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    pcm = _ensure_mono_int16(audio)
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path

def assemblyai_transcribe_wav(wav_bytes: bytes) -> str:
    """Transcribe WAV audio bytes using AssemblyAI.

    Reads API key from the ASSEMBLYAI_API_KEY environment variable.
    Returns empty string on failure.
    """
    api_key = os.getenv(AAI_KEY_ENV)
    if not api_key or api_key == "your_assemblyai_api_key_here":
        print("\n[ERROR] AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY in .env")
        print("You can get a free API key at https://app.assemblyai.com/signup")
        return ""

    try:
        headers = {"authorization": api_key}

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
        for _ in range(30):  # Wait up to ~24 seconds
            time.sleep(0.8)
            status_response = requests.get(
                f"https://api.assemblyai.com/v2/transcripts/{transcript_id}",
                headers=headers,
                timeout=60
            )
            status_response.raise_for_status()
            data = status_response.json()

            if data.get("status") == "completed":
                text = (data.get("text") or "").strip()
                if text:
                    print("[STT] Transcription successful!")
                return text

            if data.get("status") == "error":
                error = data.get("error", "Unknown error")
                print(f"[STT] Transcription failed: {error}")
                return ""

        print("[STT] Transcription timed out")
        return ""

    except requests.exceptions.RequestException as e:
        print(f"[STT] API request failed: {e}")
        return ""

def _ensure_mono_int16(arr: np.ndarray) -> np.ndarray:
    """Convert an array to mono int16 PCM."""
    if arr.ndim > 1:
        arr = arr[:, 0]
    if arr.dtype == np.float32 or arr.dtype == np.float64:
        arr = np.clip(arr, -1.0, 1.0)
        arr = (arr * 32767.0).astype(np.int16)
    elif arr.dtype != np.int16:
        arr = arr.astype(np.int16, copy=False)
    return arr

def _wav_bytes_from_pcm16(pcm: np.ndarray, sr: int = SR) -> bytes:
    """Wrap mono int16 PCM samples into a WAV byte stream."""
    pcm = _ensure_mono_int16(pcm)
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()

def record_ptt(device: Optional[int] = None) -> np.ndarray:
    """Record audio until the user presses Enter again (push-to-talk).

    Returns mono int16 numpy array at SR.
    """
    stop_event = threading.Event()
    frames: list[np.ndarray] = []

    def _input_waiter():
        try:
            input()  # Wait for Enter to stop
        finally:
            stop_event.set()

    def _callback(indata, frames_count, time_info, status):  # sounddevice callback
        if status:
            log.warning(f"InputStream status: {status}")
        frames.append(indata.copy())

    waiter = threading.Thread(target=_input_waiter, daemon=True)
    waiter.start()

    blocksize = int(SR * (BLOCK_MS / 1000.0))
    with sd.InputStream(samplerate=SR, channels=1, dtype='int16',
                        device=device, blocksize=blocksize, callback=_callback):
        while not stop_event.is_set():
            time.sleep(0.05)

    if frames:
        audio = np.concatenate(frames, axis=0).reshape(-1)
    else:
        audio = np.zeros((0,), dtype=np.int16)
    return audio

def _record_utterance(
    device: Optional[int] = None,
    threshold: int = THRESHOLD,
    min_talk_ms: int = MIN_TALK_MS,
    tail_sil_ms: int = TAIL_SIL_MS,
    max_utter_ms: int = MAX_UTTER_MS,
) -> np.ndarray:
    """Simple amplitude-based VAD recording. Returns mono int16 samples.

    Starts when energy exceeds threshold for at least min_talk_ms and
    stops after tail_sil_ms of silence or when max_utter_ms is reached.
    """
    block_len = int(SR * (BLOCK_MS / 1000.0))
    max_blocks = int(max_utter_ms / BLOCK_MS)
    tail_blocks = int(tail_sil_ms / BLOCK_MS)
    min_talk_blocks = max(1, int(min_talk_ms / BLOCK_MS))

    started = False
    above_count = 0
    silence_count = 0

    captured: list[np.ndarray] = []

    def _rms_int16(x: np.ndarray) -> float:
        x = x.astype(np.int32)
        return float(np.sqrt(np.mean((x * x))))

    with sd.InputStream(samplerate=SR, channels=1, dtype='int16', device=device,
                        blocksize=block_len) as stream:
        total_blocks = 0
        while True:
            data, _ = stream.read(block_len)
            data = data.reshape(-1)
            total_blocks += 1

            # Compute simple energy metric
            energy = _rms_int16(data)

            if not started:
                if energy >= threshold:
                    above_count += 1
                else:
                    above_count = 0

                if above_count >= min_talk_blocks:
                    started = True
                    _cue_start()
                    captured.append(data.copy())
            else:
                captured.append(data.copy())
                if energy < threshold:
                    silence_count += 1
                else:
                    silence_count = 0

                if silence_count >= tail_blocks:
                    _cue_end()
                    break

            if started and total_blocks >= max_blocks:
                _cue_end()
                break

    if captured:
        return np.concatenate(captured).astype(np.int16)
    return np.zeros((0,), dtype=np.int16)

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
    no_tts: bool = False,
    device: Optional[int] = None,
    threshold: int = THRESHOLD,
    wake_word: Optional[str] = None,
    state: Optional[dict] = None,
) -> None:
    """Run the main voice interaction loop.
    
    Args:
        generate_text: Function that processes user text and returns response
        mode: 'ptt' for push-to-talk or 'auto' for voice activity detection
        no_tts: If True, only print responses instead of using TTS
    """
    log.info(f"Starting voice loop in {mode} mode" + (" (No TTS)" if no_tts else ""))
    
    def _handle_settings(cmd: str) -> Optional[str]:
        nonlocal threshold, wake_word
        t = _normalize(cmd)
        # set threshold to N
        m = re.match(r"^set (?:the )?threshold (?:to|=)\s*(\d{2,5})$", t)
        if m:
            try:
                val = int(m.group(1))
                threshold = val
                if state is not None:
                    state["threshold"] = val
                return f"[settings] Threshold set to {val}"
            except Exception:
                return "[settings] Invalid threshold value"

        # set wake word to X
        m = re.match(r"^set (?:the )?wake\s*word (?:to|=)\s*(.+)$", t)
        if m:
            ww = m.group(1).strip()
            wake_word = ww or None
            if state is not None:
                state["wake_word"] = wake_word
            return f"[settings] Wake word set to '{wake_word or 'OFF'}'"

        # disable wake word
        if t in ("disable wake word", "turn off wake word", "wake word off"):
            wake_word = None
            if state is not None:
                state["wake_word"] = None
            return "[settings] Wake word disabled"

        return None

    try:
        consecutive_errors = 0
        while True:
            response = ""
            try:
                if mode == "ptt":
                    print("\n[PTT] Press Enter to speak (press Enter again to stop)...")
                    input()  # Wait for first Enter

                    # Record audio
                    print("[PTT] Recording... Press Enter to stop.")
                    _cue_start()
                    audio_data = record_ptt(device=device)
                    _cue_end()
                    if audio_data.size == 0:
                        print("[PTT] No audio captured. Try again.")
                        continue

                    # Convert to WAV and transcribe
                    wav_bytes = _wav_bytes_from_pcm16(audio_data)
                    user_text = assemblyai_transcribe_wav(wav_bytes)
                    if not user_text:
                        print("[PTT] No speech detected or STT failed. Try again.")
                        continue

                    print(f"[PTT] You said: {user_text}")
                    msg = _handle_settings(user_text)
                    if msg:
                        print(msg)
                        continue
                    cmd = _extract_after_wake(user_text, wake_word)
                    if cmd is None:
                        print(f"[wake] Ignored: {user_text!r}")
                        continue
                    user_text = cmd

                    # Process the command
                    response = generate_text(user_text)
                    print(f"[agent] {response}")

                    # Only use TTS if not in NoTTS mode (disabled in this project)
                    if not no_tts and response:
                        pass

                elif mode == "auto":
                    audio_data = listen_once_auto(device=device, threshold=threshold)
                    if audio_data.size == 0:
                        print("[listen] No audio captured.")
                        continue
                    user_text = stt_transcribe(audio_data)
                    if not user_text:
                        print("[stt] Empty transcription.")
                        continue
                    # allow settings changes pre-wake-word (so "set threshold ..." works with disabled wake word)
                    msg = _handle_settings(user_text)
                    if msg:
                        print(msg)
                        continue

                    cmd = _extract_after_wake(user_text, wake_word)
                    if cmd is None:
                        print(f"[wake] Ignored: {user_text!r}")
                        continue
                    user_text = cmd
                    print(f"[stt] You said: {user_text}")
                    response = generate_text(user_text)
                    print(f"[agent] {response}")
                    if not no_tts and response:
                        pass

                consecutive_errors = 0

            except KeyboardInterrupt:
                log.info("Loop interrupted by user")
                break
            except NameError as e:
                log.error(f"Fatal NameError in voice loop: {e}", exc_info=True)
                break
            except Exception as e:
                consecutive_errors += 1
                log.error(f"Error in voice loop (#{consecutive_errors}): {e}", exc_info=True)
                time.sleep(min(2.0, 0.2 * consecutive_errors))

    except Exception as e:
        log.error(f"Fatal error in voice loop: {e}", exc_info=True)
    finally:
        log.info("Voice loop stopped")
