# quick_voice_test.ps1  (debug version)

# resolve text
$Text = if ($args.Count -gt 0) { $args -join ' ' } else { 'Hello, this is a quick ElevenLabs voice test.' }

Write-Host "`n=== Quick Voice Test ===" -ForegroundColor Cyan
Write-Host ("Text: {0}" -f $Text) -ForegroundColor DarkCyan

# load .env -> process env
$envPath = Join-Path $PSScriptRoot '..\.env'
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.+)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
} else {
    Write-Warning ("No .env found at {0}" -f $envPath)
}

# creds
$apiKey = $env:ELEVENLABS_API_KEY
if (-not $apiKey) { 
    Write-Error 'ELEVENLABS_API_KEY missing' 
    exit 1 
}

# Get available voices
Write-Host "`n[1/3] Fetching available voices..." -ForegroundColor Cyan
$headers = @{ 
    'xi-api-key' = $apiKey
    'accept' = 'application/json'
}

try {
    $response = Invoke-WebRequest -Uri 'https://api.elevenlabs.io/v1/voices' -Headers $headers -Method Get -ErrorAction Stop
    $voices = $response.Content | ConvertFrom-Json
    
    if ($voices.voices.Count -eq 0) { 
        Write-Error 'No voices found in your ElevenLabs account.'
        exit 1 
    }
    
    $voiceId = $voices.voices[0].voice_id
    $voiceName = $voices.voices[0].name
    Write-Host ("[+] Using voice: {0} (ID: {1})" -f $voiceName, $voiceId) -ForegroundColor Green
    
} catch {
    Write-Error ("Failed to fetch voices: {0}" -f $_.Exception.Message)
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        $reader.Dispose()
        Write-Host "[!] Error Response: $errorBody" -ForegroundColor Red
    }
    exit 1
}

# Prepare TTS request
$headers = @{ 
    'xi-api-key' = $apiKey
    'Content-Type' = 'application/json'
    'accept' = 'audio/mpeg'
}

$body = @{
    text = $Text
    model_id = 'eleven_multilingual_v2'
    voice_settings = @{ 
        stability = 0.5 
        similarity_boost = 0.5 
    }
}

$bodyJson = $body | ConvertTo-Json -Depth 5 -Compress

# Debug output
Write-Host "`n[2/3] Sending TTS request..." -ForegroundColor Cyan
Write-Host ("    URL: https://api.elevenlabs.io/v1/text-to-speech/{0}" -f $voiceId) -ForegroundColor DarkGray
Write-Host ("    Model: {0}" -f $body.model_id) -ForegroundColor DarkGray

# send + play
$out = Join-Path $env:TEMP ("tts_quick_{0}.mp3" -f (Get-Random))
try {
    $response = Invoke-WebRequest -Uri ("https://api.elevenlabs.io/v1/text-to-speech/{0}" -f $voiceId) `
                -Method Post -Headers $headers -Body $bodyJson -OutFile $out -ErrorAction Stop
    
    Write-Host "`n[3/3] Success!" -ForegroundColor Green
    Write-Host ("    Audio saved to: {0}" -f $out) -ForegroundColor Green
    
    if (Test-Path $out) {
        Start-Process $out
    } else {
        Write-Error "Output file was not created"
    }
    
} catch {
    Write-Host "`n[!] TTS Request Failed" -ForegroundColor Red
    $errorResponse = $_.Exception.Response
    
    if ($errorResponse) {
        Write-Host ("    Status: {0} {1}" -f [int]$errorResponse.StatusCode, $errorResponse.StatusDescription) -ForegroundColor Red
        
        try {
            $reader = New-Object System.IO.StreamReader($errorResponse.GetResponseStream())
            $errorBody = $reader.ReadToEnd()
            $reader.Dispose()
            
            if ($errorBody) {
                Write-Host "    Error Details:" -ForegroundColor Red
                try {
                    $errorJson = $errorBody | ConvertFrom-Json -ErrorAction Stop
                    if ($errorJson.detail) {
                        $errorJson.detail | Format-List * -Force | Out-String | ForEach-Object { 
                            Write-Host ("    {0}" -f $_.Trim()) -ForegroundColor Red 
                        }
                    } else {
                        Write-Host ("    {0}" -f $errorBody) -ForegroundColor Red
                    }
                } catch {
                    Write-Host ("    {0}" -f $errorBody) -ForegroundColor Red
                }
            }
        } catch {
            Write-Host ("    Could not read response: {0}" -f $_.Exception.Message) -ForegroundColor Red
        }
    } else {
        Write-Host ("    Error: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }
    
    exit 1
}

Write-Host "`n=== Test Complete ===`n" -ForegroundColor Cyan
