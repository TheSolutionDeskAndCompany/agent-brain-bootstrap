# voice_sanity_check.ps1 — STT(AssemblyAI) + TTS(ElevenLabs) in one go
# Usage:  & .\scripts\voice_sanity_check.ps1

Write-Host "=== Voice Sanity Check (STT -> TTS) ===" -ForegroundColor Cyan

# ---- Load .env into process env ----
$envPath = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envPath) {
  Get-Content $envPath | ForEach-Object {
    if ($_ -match "^\s*([^#=]+?)\s*=\s*(.+)$") {
      [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
  }
}

# ---- Read keys / defaults ----
$aaiKey = $env:ASSEMBLYAI_API_KEY
$elKey  = $env:ELEVENLABS_API_KEY
$voice  = if ($env:ELEVENLABS_VOICE_ID) { $env:ELEVENLABS_VOICE_ID } else { "21m00Tcm4TlvDq8ikWAM" }  # Rachel

if (-not $aaiKey) { Write-Error "ASSEMBLYAI_API_KEY missing in .env"; exit 1 }
if (-not $elKey)  { Write-Error "ELEVENLABS_API_KEY missing in .env"; exit 1 }

# ---- Set Python path ----
$pythonPath = "C:\Users\aboud\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $pythonPath)) {
    Write-Error "Python not found at $pythonPath"; exit 1
}

# ---- Ensure Python deps are installed ----
Write-Host "`n[1/4] Checking Python dependencies..." -ForegroundColor Cyan
& $pythonPath -m pip install --disable-pip-version-check --quiet sounddevice numpy scipy requests python-dotenv
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Python dependencies"; exit 1
}

# ---- Write a temp Python script to record & transcribe ----
$pyCode = @'
import os, sys, time, json, requests, tempfile
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

AAI_KEY = os.environ.get("ASSEMBLYAI_API_KEY")
DURATION = 5  # seconds
SR = 16000

def upload(filepath):
    headers = {"authorization": AAI_KEY}
    with open(filepath, "rb") as f:
        resp = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, data=f)
    resp.raise_for_status()
    return resp.json()["upload_url"]

def transcribe(audio_url):
    headers = {"authorization": AAI_KEY, "content-type": "application/json"}
    job = requests.post("https://api.assemblyai.com/v2/transcript", headers=headers, json={"audio_url": audio_url})
    job.raise_for_status()
    tid = job.json()["id"]
    while True:
        r = requests.get(f"https://api.assemblyai.com/v2/transcript/{tid}", headers=headers)
        r.raise_for_status()
        j = r.json()
        if j["status"] == "completed":
            return j.get("text","")
        if j["status"] == "error":
            raise RuntimeError(j.get("error","transcription failed"))
        time.sleep(1)

def main():
    print("Recording...", flush=True)
    try:
        audio = sd.rec(int(DURATION*SR), samplerate=SR, channels=1, dtype="int16")
        sd.wait()
        wav_path = tempfile.mktemp(suffix=".wav")
        wav_write(wav_path, SR, audio)
        print("Uploading...", flush=True)
        url = upload(wav_path)
        print("Transcribing...", flush=True)
        text = transcribe(url) or ""
        print(text.strip())
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
'@

$pyFile = Join-Path $env:TEMP "aai_sanity.py"
Set-Content -Path $pyFile -Value $pyCode -Encoding ascii

# ---- Run it and capture transcript ----
Write-Host "`n[2/4] Recording audio (5 seconds)..." -ForegroundColor Cyan
$transcript = & $pythonPath $pyFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error ("Python script failed: {0}" -f ($transcript -join "`n"))
    exit 1
}

$transcript = ($transcript | Select-Object -Last 1).Trim()
if (-not $transcript) {
    Write-Warning "No transcript received. Using fallback text."
    $transcript = "Microphone and network test complete. Text to speech fallback."
}

Write-Host ("`n[3/4] Transcript: {0}" -f $transcript) -ForegroundColor DarkCyan

# ---- ElevenLabs TTS ----
$headers = @{
    "xi-api-key"   = $elKey
    "Accept"       = "audio/mpeg"
    "Content-Type" = "application/json"
}

$body = @{
    text = $transcript
    model_id = "eleven_multilingual_v2"
    voice_settings = @{ 
        stability = 0.5 
        similarity_boost = 0.5 
    }
} | ConvertTo-Json -Depth 5

$out = Join-Path $env:TEMP ("voice_sanity_{0}.mp3" -f (Get-Random))

Write-Host "`n[4/4] Converting to speech..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri ("https://api.elevenlabs.io/v1/text-to-speech/{0}" -f $voice) `
                -Method Post -Headers $headers -Body $body -OutFile $out -ErrorAction Stop
    
    Write-Host ("`n✅ Success! Audio saved to: {0}" -f $out) -ForegroundColor Green
    Start-Process $out
} catch {
    Write-Error ("TTS failed: {0}" -f $_.Exception.Message)
    if ($_.Exception.Response) {
        try {
            $sr = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host ("Response Body: {0}" -f $sr.ReadToEnd()) -ForegroundColor Red
        } catch { }
    }
    exit 1
}

Write-Host "`n=== Done ===`n" -ForegroundColor Cyan
