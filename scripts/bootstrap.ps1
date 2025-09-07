Param(
  [string]$Repo = "ORG/REPO",
  [string]$AssetName = "AgentBrain-Setup.exe"
)

Write-Host "AgentBrain bootstrap starting..."

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$releasesUrl = "https://api.github.com/repos/$Repo/releases/latest"
$release = Invoke-RestMethod -Uri $releasesUrl -UseBasicParsing

$asset = $release.assets | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1
if (-not $asset) { Write-Error "Could not find $AssetName"; exit 1 }

$temp = Join-Path $env:TEMP $AssetName
Write-Host "Downloading $AssetName..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $temp

$checksumAsset = $release.assets | Where-Object { $_.name -eq "$($AssetName).sha256.txt" } | Select-Object -First 1
if ($checksumAsset) {
  $shaFile = Join-Path $env:TEMP "$($AssetName).sha256.txt"
  Invoke-WebRequest -Uri $checksumAsset.browser_download_url -OutFile $shaFile
  $expected = (Get-Content $shaFile | Select-Object -Last 1).Split()[-1]
  $actual = (Get-FileHash -Path $temp -Algorithm SHA256).Hash
  if ($expected.ToUpper() -ne $actual.ToUpper()) {
    Write-Error "Checksum mismatch. Aborting."
    exit 1
  }
}

Write-Host "Running installer silently..."
Start-Process -FilePath $temp -ArgumentList "/VERYSILENT" -Wait
Write-Host "Done. AgentBrain is installed."

